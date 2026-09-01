#!/usr/bin/env python3
"""
OntoX5 Server — plateforme d'ontologie de conformité, souveraine.

CE QUE C'EST
Un service qui transforme une spécification métier en ontologie exécutable,
la sert à des agents, et refuse les substitutions non autorisées.

CE QUE ÇA N'EST PAS
Un triplestore. Le magasin en mémoire suffit pour un domaine réglementaire
(quelques milliers de triplets). Pour de l'échelle, on branche Stardog ou
GraphDB derrière : l'audit de portabilité établit que le modèle s'y charge
sans modification.

SOUVERAINETÉ
Aucun appel sortant. Aucune télémétrie. Le processus tourne dans le
périmètre du client, sur ses données, et n'écrit que dans le dossier
qu'on lui désigne.

    pip install fastapi uvicorn pyyaml rdflib pyshacl python-multipart
    python3 server/app.py            # http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import pathlib
import sys
import time
import uuid
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from rdflib import Graph, URIRef, BNode

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))
import generate as gen  # noqa: E402

# --------------------------------------------------------------------------
# Magasin en mémoire. Un domaine = une ontologie + ses formes + ses données.
# --------------------------------------------------------------------------

class Domain:
    def __init__(self, did: str, spec: dict):
        self.id = did
        self.spec = spec
        self.name = spec.get("domaine", {}).get("nom", did)
        self.created = time.time()

        self.ontology_ttl = gen.generate_ontology(spec)
        self.shapes_ttl, self.decisions = gen.generate_shapes(spec)
        self.report_md = gen.generate_report(spec, self.decisions)

        self.g = Graph()
        self.g.parse(data=self.ontology_ttl, format="turtle")
        self.shapes = Graph()
        self.shapes.parse(data=self.shapes_ttl, format="turtle")
        self.data_triples = 0

    def load_data(self, text: str, fmt: str = "turtle") -> int:
        before = len(self.g)
        self.g.parse(data=text, format=fmt)
        added = len(self.g) - before
        self.data_triples += added
        return added

    def summary(self) -> dict:
        hard = sum(1 for d in self.decisions if d.get("severite") == "sh:Violation")
        soft = len(self.decisions) - hard
        degraded = sum(1 for d in self.decisions if d.get("degrade"))
        return {
            "id": self.id,
            "name": self.name,
            "triples": len(self.g),
            "data_triples": self.data_triples,
            "shape_triples": len(self.shapes),
            "hard_constraints": hard,
            "soft_signals": soft,
            "degraded_barriers": degraded,
        }


DOMAINS: dict[str, Domain] = {}


def _guess_ns(g: Graph) -> str:
    """Déduit l'espace de noms du modèle à partir des prédicats présents."""
    for _, p, _ in g:
        sp = str(p)
        if sp.endswith("mappingRelation"):
            return sp[: -len("mappingRelation")]
    return "https://agenticx5.com/ont/compliance#"

# --------------------------------------------------------------------------

app = FastAPI(
    title="OntoX5 Server",
    version="0.1.0",
    description=(
        "Plateforme d'ontologie de conformité souveraine. "
        "Spécification métier en entrée, ontologie exécutable en sortie, "
        "barrière de substitution pour les agents."
    ),
)


@app.get("/health", tags=["système"])
def health():
    return {"status": "ok", "domains": len(DOMAINS), "sovereign": True,
            "outbound_calls": 0}


# ---------------------------------------------------------------- domaines

@app.post("/domains", tags=["domaines"], status_code=201)
async def create_domain(spec: UploadFile = File(..., description="spec YAML de domaine")):
    """Une spécification métier entre. Une ontologie, des contraintes et un
    rapport de décisions sortent. C'est l'opération qui distingue cette
    plateforme d'un éditeur d'ontologie : on ne dessine pas des classes, on
    décrit un domaine et on assume les décisions générées."""
    raw = (await spec.read()).decode("utf-8")
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise HTTPException(400, f"YAML invalide : {e}")
    if not isinstance(parsed, dict):
        raise HTTPException(400, "La spec doit être un objet YAML.")

    did = parsed.get("domaine", {}).get("prefixe") or uuid.uuid4().hex[:8]
    if did in DOMAINS:
        raise HTTPException(409, f"Le domaine « {did} » existe déjà.")
    try:
        d = Domain(did, parsed)
    except Exception as e:
        raise HTTPException(422, f"Génération impossible : {e}")
    DOMAINS[did] = d
    return d.summary()


@app.get("/domains", tags=["domaines"])
def list_domains():
    return [d.summary() for d in DOMAINS.values()]


def _dom(did: str) -> Domain:
    if did not in DOMAINS:
        raise HTTPException(404, f"Domaine « {did} » inconnu.")
    return DOMAINS[did]


@app.get("/domains/{did}/ontology.ttl", tags=["domaines"], response_class=PlainTextResponse)
def get_ontology(did: str):
    return PlainTextResponse(_dom(did).ontology_ttl, media_type="text/turtle")


@app.get("/domains/{did}/shapes.ttl", tags=["domaines"], response_class=PlainTextResponse)
def get_shapes(did: str):
    return PlainTextResponse(_dom(did).shapes_ttl, media_type="text/turtle")


@app.get("/domains/{did}/decisions.md", tags=["domaines"], response_class=PlainTextResponse)
def get_decisions(did: str):
    """Le rapport de décisions. Ce que le générateur a choisi, et ce qu'il a
    refusé de faire — notamment les barrières dégradées en avertissement
    parce qu'une contrainte que les gens contournent est pire qu'aucune
    contrainte."""
    return PlainTextResponse(_dom(did).report_md, media_type="text/markdown")


@app.post("/domains/{did}/data", tags=["domaines"])
async def load_data(did: str, file: UploadFile = File(...), fmt: str = "turtle"):
    d = _dom(did)
    raw = (await file.read()).decode("utf-8")
    try:
        n = d.load_data(raw, fmt)
    except Exception as e:
        raise HTTPException(422, f"Chargement impossible : {e}")
    return {"loaded_triples": n, **d.summary()}


# ---------------------------------------------------------------- requêtes

class QueryIn(BaseModel):
    query: str = Field(..., description="SPARQL 1.1 — SELECT, ASK, CONSTRUCT ou DESCRIBE")


@app.post("/domains/{did}/query", tags=["requêtes"])
def run_query(did: str, body: QueryIn):
    """Les quatre formes, parce que le consommateur décide de la forme :
    un humain lit un tableau, un agent a besoin d'un booléen avant d'agir,
    un système en aval veut un sous-graphe, une interface veut une fiche."""
    d = _dom(did)
    try:
        res = d.g.query(body.query)
    except Exception as e:
        raise HTTPException(400, f"Requête invalide : {e}")

    if res.type == "ASK":
        return {"form": "ASK", "boolean": bool(res)}
    if res.type in ("CONSTRUCT", "DESCRIBE"):
        return {"form": res.type,
                "triples": len(res.graph),
                "turtle": res.graph.serialize(format="turtle")}
    cols = [str(v) for v in res.vars]
    rows = []
    for r in res:
        row = {}
        for v in res.vars:
            val = r[v]
            if val is None:
                continue
            term = {"value": str(val)}
            if isinstance(val, URIRef):
                term["type"] = "uri"
            elif isinstance(val, BNode):
                term["type"] = "bnode"
            else:
                term["type"] = "literal"
                if getattr(val, "language", None):
                    term["xml:lang"] = val.language
                if getattr(val, "datatype", None):
                    term["datatype"] = str(val.datatype)
            row[str(v)] = term
        rows.append(row)
    return {"form": "SELECT", "columns": cols, "rows": rows}


# ---------------------------------------------------------------- validation

@app.get("/domains/{did}/validate", tags=["gouvernance"])
def validate_domain(did: str):
    """Le verdict SHACL. Deux niveaux : violation quand la donnée produit une
    réponse fausse, avertissement quand elle est seulement incomplète."""
    d = _dom(did)
    try:
        from pyshacl import validate as shacl_validate
    except ImportError:
        raise HTTPException(501, "pyshacl n'est pas installé.")
    conforms, _, txt = shacl_validate(d.g, shacl_graph=d.shapes,
                                      inference="none", abort_on_first=False)
    v = txt.count("Severity: sh:Violation")
    w = txt.count("Severity: sh:Warning")
    targeted = _targeted_nodes(d)
    return {"conforms": conforms,
            "violations": v,
            "warnings": w,
            "targeted_nodes": targeted,
            "vacuous": targeted == 0,
            "note": ("AUCUN nœud ciblé : les formes et les données n'utilisent pas "
                     "le même vocabulaire. Un verdict « conforme » sur zéro nœud "
                     "ne prouve rien." if targeted == 0 else None),
            "report": txt}


def _targeted_nodes(d: "Domain") -> int:
    from rdflib.namespace import RDF
    from rdflib import URIRef
    SH = "http://www.w3.org/ns/shacl#"
    classes = set(d.shapes.objects(None, URIRef(SH + "targetClass")))
    return sum(1 for c in classes for _ in d.g.subjects(RDF.type, c))


# ---------------------------------------------------------------- barrière

class GuardIn(BaseModel):
    source: str = Field(..., description="URI ou étiquette du concept d'origine")
    target: str = Field(..., description="URI ou étiquette du concept cible")
    min_confidence: float = Field(0.95, ge=0, le=1)
    require_human_review: bool = True
    namespace: str | None = Field(None, description="espace de noms du modèle; déduit si absent")


@app.post("/domains/{did}/guard", tags=["agents"])
def guard(did: str, body: GuardIn):
    """LA BARRIÈRE.

    Un agent demande : puis-je remplacer ce concept par cet autre sans
    prévenir personne ? exactMatch n'est pas une observation sur le monde,
    c'est une permission. Elle se vérifie avant d'agir.

    Réponse booléenne, plus la raison du refus — un agent n'a pas besoin
    d'un tableau, il a besoin d'un feu vert ou rouge."""
    d = _dom(did)
    ns = body.namespace or _guess_ns(d.g)
    q = f"""
    PREFIX ax5:  <{ns}>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT ?rel ?conf ?status WHERE {{
      ?m ax5:mapsFrom ?a ;
         ax5:mapsTo   ?b ;
         ax5:mappingRelation ?rel .
      OPTIONAL {{ ?m ax5:confidence   ?conf }}
      OPTIONAL {{ ?m ax5:reviewStatus ?status }}
      FILTER( CONTAINS(STR(?a), "{body.source}")
              || EXISTS {{ ?a skos:prefLabel ?la . FILTER(CONTAINS(STR(?la), "{body.source}")) }} )
      FILTER( CONTAINS(STR(?b), "{body.target}")
              || EXISTS {{ ?b skos:prefLabel ?lb . FILTER(CONTAINS(STR(?lb), "{body.target}")) }} )
    }}
    """
    try:
        rows = list(d.g.query(q))
    except Exception as e:
        raise HTTPException(400, f"Vérification impossible : {e}")

    if not rows:
        return {"allowed": False,
                "reason": "no_mapping",
                "detail": "Aucune correspondance déclarée entre ces deux concepts. "
                          "L'absence de correspondance n'est pas une équivalence."}

    best = None
    for r in rows:
        conf = float(r[1]) if r[1] is not None else 0.0
        rel = str(r[0])
        status = str(r[2]) if r[2] is not None else ""
        cand = {"relation": rel, "confidence": conf, "review_status": status}
        if best is None or conf > best["confidence"]:
            best = cand

    reasons = []
    if not best["relation"].endswith("exactMatch"):
        reasons.append("relation_not_exact_match")
    if best["confidence"] < body.min_confidence:
        reasons.append("confidence_below_threshold")
    if body.require_human_review and best["review_status"] != "human-reviewed":
        reasons.append("not_human_reviewed")

    return {
        "allowed": not reasons,
        "reason": None if not reasons else reasons,
        "mapping": best,
        "policy": {"min_confidence": body.min_confidence,
                   "require_human_review": body.require_human_review},
        "detail": ("Substitution autorisée." if not reasons else
                   "Substitution refusée. Une correspondance qui ne satisfait "
                   "pas la politique ne fonde aucune décision engageante."),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
