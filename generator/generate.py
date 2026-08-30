#!/usr/bin/env python3
"""
GÉNÉRATEUR ONTOLOGIQUE AX5
==========================

Prend un spec de domaine écrit en langage métier (YAML) et produit :

    1. une ontologie OWL          (les classes et les propriétés)
    2. des shapes SHACL           (les contraintes de qualité)
    3. un rapport de décisions    (pourquoi chaque sévérité a été choisie)

Le troisième artefact est le plus important. Un générateur qui produit du
RDF sans expliquer ses choix déplace le problème : l'utilisateur se
retrouve avec un fichier qu'il ne peut pas défendre en revue.

Usage :
    python generate.py specs/sst-quebec.yml --out ../generated/
"""

import argparse
import sys
from pathlib import Path

import yaml

from severity_policy import Severity, propose_severity, decide_severity


# ---------------------------------------------------------------------
# Traduction des types métier vers XSD
# ---------------------------------------------------------------------

TYPE_MAP = {
    "texte": "xsd:string",
    "date": "xsd:date",
    "horodatage": "xsd:dateTime",
    "decimal": "xsd:decimal",
    "entier": "xsd:integer",
    "booleen": "xsd:boolean",
}


def qname(prefix: str, name: str) -> str:
    return f"{prefix}:{name}"


# ---------------------------------------------------------------------
# 1. GÉNÉRATION DE L'ONTOLOGIE
# ---------------------------------------------------------------------

def generate_ontology(spec: dict) -> str:
    d = spec["domaine"]
    p = d["prefixe"]
    lines = [
        f"@prefix {p}:  <{d['uri']}> .",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix dct:  <http://purl.org/dc/terms/> .",
        "",
        "#" * 69,
        f"# {d['nom']}",
        f"# Généré par ax5-onto/generator — version {d.get('version', '0.1.0')}",
        "#",
        "# Ce fichier est GÉNÉRÉ. Modifier le spec, pas le fichier.",
        "#" * 69,
        "",
        f"{p}: a owl:Ontology ;",
        f'    dct:title "{d["nom"]}"@fr ;',
        f'    owl:versionInfo "{d.get("version", "0.1.0")}" .',
        "",
    ]

    seen_props: set[str] = set()

    for fiche in spec["fiches"]:
        cls = qname(p, fiche["nom"])
        lines.append("#" + "-" * 68)
        if fiche.get("description"):
            for ligne in _wrap_comment(fiche["description"]):
                lines.append(f"# {ligne}")
        lines.append("#" + "-" * 68)
        lines.append(f"{cls} a owl:Class ;")
        lines.append(f'    rdfs:label "{fiche["nom"]}"@fr .')
        lines.append("")

        for champ in fiche["champs"]:
            prop = qname(p, champ["nom"])
            if prop in seen_props:
                continue
            seen_props.add(prop)

            is_link = champ["type"] == "lien"
            kind = "owl:ObjectProperty" if is_link else "owl:DatatypeProperty"
            rng = (
                qname(p, champ["vers"]) if is_link
                else TYPE_MAP.get(champ["type"], "xsd:string")
            )

            lines.append(f"{prop} a {kind} ;")
            if champ.get("libelle"):
                lines.append(f'    rdfs:label "{champ["libelle"]}"@fr ;')
            lines.append(f"    rdfs:domain {cls} ;")
            lines.append(f"    rdfs:range {rng} .")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------
# 2. GÉNÉRATION DES SHAPES
# ---------------------------------------------------------------------

def generate_shapes(spec: dict) -> tuple[str, list[dict]]:
    """Retourne le fichier SHACL et le journal des décisions de sévérité."""
    d = spec["domaine"]
    p = d["prefixe"]
    decisions: list[dict] = []

    lines = [
        f"@prefix {p}:  <{d['uri']}> .",
        "@prefix sh:   <http://www.w3.org/ns/shacl#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "#" * 69,
        f"# CONTRAINTES — {d['nom']}",
        "#",
        "# Chaque sévérité porte en commentaire le test qui l'a produite.",
        "# Voir generator/severity_policy.py pour les trois tests.",
        "#" * 69,
        "",
    ]

    for fiche in spec["fiches"]:
        cls = qname(p, fiche["nom"])
        shape = qname(p, fiche["nom"] + "Shape")
        lines.append("#" + "-" * 68)
        lines.append(f"# {fiche['nom']}")
        lines.append("#" + "-" * 68)
        lines.append(f"{shape} a sh:NodeShape ;")
        lines.append(f"    sh:targetClass {cls} ;")
        lines.append("")

        blocks = []
        for champ in fiche["champs"]:
            if not champ.get("obligatoire") and "min" not in champ:
                continue

            dec = _severity_for(champ)
            decisions.append({
                "fiche": fiche["nom"],
                "champ": champ["nom"],
                "declare": "obligatoire" if champ.get("obligatoire") else "borné",
                "severite": dec.severity.value,
                "test": dec.failed_test,
                "justification": dec.rationale,
                "degrade": (
                    champ.get("obligatoire")
                    and dec.severity is not Severity.VIOLATION
                ),
            })

            b = ["    sh:property ["]
            b.append(f"        sh:path {qname(p, champ['nom'])} ;")
            if champ.get("obligatoire"):
                b.append("        sh:minCount 1 ;")
            if champ.get("unique"):
                b.append("        sh:maxCount 1 ;")
            if champ["type"] == "lien":
                b.append(f"        sh:class {qname(p, champ['vers'])} ;")
            else:
                b.append(f"        sh:datatype {TYPE_MAP.get(champ['type'], 'xsd:string')} ;")
            if "min" in champ:
                b.append(f"        sh:minInclusive {champ['min']} ;")
            if "max" in champ:
                b.append(f"        sh:maxInclusive {champ['max']} ;")
            b.append(f"        sh:severity {dec.severity.value} ;")
            b.append(f'        sh:message "{_esc(dec.rationale)}" ;')
            b.append(f"        # {dec.failed_test}")
            b.append("    ]")
            blocks.append("\n".join(b))

        lines.append(" ;\n".join(blocks) + " .")
        lines.append("")

    # Règles métier -> SHACL-SPARQL
    for regle in spec.get("regles", []):
        lines.extend(_generate_rule(regle, spec))
        lines.append("")

    return "\n".join(lines), decisions


def _severity_for(champ: dict):
    """Le spec peut forcer une sévérité; sinon on applique la politique."""
    if "severite" in champ:
        return decide_severity(
            produces_wrong_answer=(champ["severite"] == "violation"),
            legitimate_data_can_fail=False,
            likely_to_be_gamed=False,
            field_name=champ["nom"],
        )
    return propose_severity(champ["nom"])


def _generate_rule(regle: dict, spec: dict) -> list[str]:
    """Traduit une règle métier en contrainte SHACL-SPARQL.

    Pourquoi du SPARQL : les composants SHACL standards contraignent UN
    chemin à la fois. Ils ne savent pas exprimer « si le champ A vaut X
    alors le champ B doit satisfaire Y », ni comparer les valeurs
    trouvées au bout de deux chemins distincts.

    Renversement à comprendre : la requête décrit ce qui est INTERDIT.
    Toute ligne retournée est une violation. Zéro ligne = conforme.
    """
    p = spec["domaine"]["prefixe"]
    uri = spec["domaine"]["uri"]
    cls = qname(p, regle["sur"])
    shape = qname(p, _camel(regle["nom"]) + "Shape")

    out = ["#" + "-" * 68]
    for ligne in _wrap_comment(regle["libelle"]):
        out.append(f"# {ligne}")
    out.append("#" + "-" * 68)
    out.append(f"{shape} a sh:NodeShape ;")
    out.append(f"    sh:targetClass {cls} ;")
    out.append("    sh:sparql [")
    out.append("        sh:severity sh:Violation ;")
    out.append(f'        sh:message "{_esc(_flat(regle["libelle"]))}" ;')
    out.append(f"        sh:prefixes {p}: ;")
    out.append('        sh:select """')

    if regle["type"] == "condition_croisee":
        out.extend(_sparql_cross_field(regle, uri))
    elif regle["type"] == "comparaison_traversee":
        out.extend(_sparql_path_compare(regle, uri))
    else:
        out.append(f"            # type de règle inconnu : {regle['type']}")

    out.append('        """ ;')
    out.append("    ] .")
    return out


def _sparql_cross_field(regle: dict, uri: str) -> list[str]:
    si, alors = regle["si"], regle["alors"]
    L = ["            SELECT $this", "            WHERE {"]

    if "vaut" in si:
        L.append(f'                $this <{uri}{si["champ"]}> "{si["vaut"]}" .')
    elif si.get("existe"):
        L.append(f"                $this <{uri}{si['champ']}> ?_a .")

    L.append(f"                $this <{uri}{alors['champ']}> ?v .")

    if "minimum" in alors:
        L.append(f"                FILTER (?v < {alors['minimum']})")
    elif "superieur_a" in alors:
        L.append(f"                $this <{uri}{alors['superieur_a']}> ?ref .")
        L.append("                FILTER (?v <= ?ref)")

    L.append("            }")
    return L


def _sparql_path_compare(regle: dict, uri: str) -> list[str]:
    c = regle["compare"]
    a = " / ".join(f"<{uri}{s}>" for s in c["chemin_a"])
    b = " / ".join(f"<{uri}{s}>" for s in c["chemin_b"])
    op = "=" if c["doivent_etre"] == "differents" else "!="
    return [
        "            SELECT $this",
        "            WHERE {",
        f"                $this {a} ?a .",
        f"                $this {b} ?b .",
        f"                FILTER (?a {op} ?b)",
        "            }",
    ]


# ---------------------------------------------------------------------
# 3. RAPPORT DE DÉCISIONS
# ---------------------------------------------------------------------

def generate_report(spec: dict, decisions: list[dict]) -> str:
    d = spec["domaine"]
    out = [
        f"# Rapport de génération — {d['nom']}",
        "",
        "Ce rapport explique **pourquoi** chaque contrainte a la sévérité",
        "qu'elle a. Il se lit sans connaître SHACL.",
        "",
        "Rappel des trois tests :",
        "",
        "1. Le défaut produit-il une réponse **fausse** ou seulement **incomplète** ?",
        "2. De la donnée **légitime** peut-elle échouer à la contrainte ?",
        "3. La contrainte serait-elle **contournée** par l'équipe d'ingestion ?",
        "",
    ]

    degrades = [x for x in decisions if x["degrade"]]
    if degrades:
        out += [
            "## ⚠ Champs dégradés par le générateur",
            "",
            "Ces champs sont déclarés obligatoires dans le spec, mais la",
            "politique de sévérité refuse d'en faire une barrière dure.",
            "",
        ]
        for x in degrades:
            out += [
                f"### `{x['fiche']}.{x['champ']}`",
                "",
                f"- Déclaré : **obligatoire**",
                f"- Généré : **{x['severite'].replace('sh:', '')}**",
                f"- Test appliqué : {x['test']}",
                f"- Raison : {x['justification']}",
                "",
            ]

    out += ["## Toutes les décisions", "", "| Fiche | Champ | Sévérité | Test |", "|---|---|---|---|"]
    for x in decisions:
        out.append(
            f"| {x['fiche']} | `{x['champ']}` | "
            f"{x['severite'].replace('sh:', '')} | {x['test']} |"
        )
    out.append("")

    v = sum(1 for x in decisions if x["severite"] == "sh:Violation")
    w = sum(1 for x in decisions if x["severite"] == "sh:Warning")
    out += [
        "## Résumé",
        "",
        f"- {v} barrières dures (Violation)",
        f"- {w} signaux doux (Warning)",
        f"- {len(spec.get('regles', []))} règles métier en SHACL-SPARQL",
        "",
        "Un ratio proche de 100 % de barrières dures est un signal d'alarme :",
        "il annonce un pipeline que l'équipe d'ingestion va contourner.",
        "",
    ]
    return "\n".join(out)


# ---------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------

def _flat(s: str) -> str:
    return " ".join(s.split())


def _esc(s: str) -> str:
    return _flat(s).replace('"', "'")


def _camel(s: str) -> str:
    return "".join(w.capitalize() for w in s.replace("-", "_").split("_"))


def _wrap_comment(s: str, width: int = 64) -> list[str]:
    words, lines, cur = _flat(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Générateur ontologique AX5")
    ap.add_argument("spec", help="fichier YAML de spec de domaine")
    ap.add_argument("--out", default="generated", help="dossier de sortie")
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    out = Path(args.out)
    (out / "ontology").mkdir(parents=True, exist_ok=True)
    (out / "shapes").mkdir(parents=True, exist_ok=True)

    p = spec["domaine"]["prefixe"]

    onto = generate_ontology(spec)
    (out / "ontology" / f"{p}.ttl").write_text(onto, encoding="utf-8")

    shapes, decisions = generate_shapes(spec)
    (out / "shapes" / f"{p}-shapes.ttl").write_text(shapes, encoding="utf-8")

    report = generate_report(spec, decisions)
    (out / "DECISIONS.md").write_text(report, encoding="utf-8")

    print("=" * 66)
    print(f"  Généré depuis : {args.spec}")
    print("=" * 66)
    print(f"  ontologie : {out / 'ontology' / (p + '.ttl')}")
    print(f"  shapes    : {out / 'shapes' / (p + '-shapes.ttl')}")
    print(f"  décisions : {out / 'DECISIONS.md'}")
    print()

    degrades = [x for x in decisions if x["degrade"]]
    if degrades:
        print("  DÉGRADATIONS (le générateur refuse la barrière dure) :")
        for x in degrades:
            print(f"    - {x['fiche']}.{x['champ']}  ->  {x['severite']}")
            print(f"      {x['test']}")
        print()

    v = sum(1 for x in decisions if x["severite"] == "sh:Violation")
    w = sum(1 for x in decisions if x["severite"] == "sh:Warning")
    print(f"  {v} barrières dures / {w} signaux doux / "
          f"{len(spec.get('regles', []))} règles SPARQL")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
