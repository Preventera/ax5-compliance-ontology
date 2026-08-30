"""
Tests de PORTABILITÉ du générateur.

CE QU'ON TESTE ICI
------------------
Pas le domaine supply chain — le fait que le générateur produise des
contraintes correctes sur un domaine qu'il n'a jamais vu, sans qu'une
seule ligne de code change.

C'est l'affirmation que le dépôt fait. Si elle n'est pas testée, ce
n'est qu'une affirmation.

CE QUE LE PORTAGE A RÉVÉLÉ
--------------------------
À la première génération : 21 barrières dures, 0 avertissement. Les
heuristiques de severity_policy.py étaient peuplées du seul vocabulaire
SST, donc `appliesToConcept` — pourtant l'exact équivalent de
`addressesHazard` — est sorti en barrière dure.

Le ratio était le signal. Un domaine sans aucun signal doux annonce un
pipeline que l'équipe d'ingestion va contourner.

Limite honnête de l'approche : les heuristiques par NOM de champ ne se
portent pas seules. Un générateur mûr déclarerait ces catégories dans le
spec plutôt que dans le code.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import SH
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "supply-chain.yml"
FIXTURE = ROOT / "tests" / "fixture_scm.ttl"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("generated_scm")
    subprocess.run(
        [sys.executable, str(ROOT / "generate.py"), str(SPEC), "--out", str(out)],
        check=True, cwd=ROOT,
    )
    return out


@pytest.fixture(scope="module")
def results(generated):
    data = Graph().parse(FIXTURE, format="turtle")
    shapes = Graph().parse(generated / "shapes" / "scm-shapes.ttl", format="turtle")
    onto = Graph().parse(generated / "ontology" / "scm.ttl", format="turtle")
    _, rg, _ = validate(data, shacl_graph=shapes, ont_graph=onto,
                        inference="none", advanced=True)
    out = []
    for res in rg.subjects(SH.focusNode, None):
        out.append({
            "node": str(rg.value(res, SH.focusNode)).split("#")[-1],
            "severity": str(rg.value(res, SH.resultSeverity)).split("#")[-1],
            "path": (str(rg.value(res, SH.resultPath)).split("#")[-1]
                     if rg.value(res, SH.resultPath) else None),
        })
    return out


def _sev(results, node):
    return {r["severity"] for r in results if r["node"] == node}


# --- Le générateur produit du RDF valide sur un domaine inconnu ------

def test_ontologie_parse(generated):
    assert len(Graph().parse(generated / "ontology" / "scm.ttl", format="turtle")) > 0


def test_shapes_parsent(generated):
    assert len(Graph().parse(generated / "shapes" / "scm-shapes.ttl", format="turtle")) > 0


# --- Le jugement de sévérité se transpose ----------------------------

def test_regle_transversale_avertit_sans_bloquer(results):
    """`appliesToConcept` est au supply chain ce que `addressesHazard`
    est à la conformité : un champ que de la donnée légitime laisse
    vide. Même test, même verdict, domaine différent.
    """
    assert _sev(results, "REGLE-TRANSVERSALE") == {"Warning"}


def test_au_moins_un_signal_doux(results):
    """Garde-fou contre la régression qui a été observée au portage.

    Un domaine généré sans aucun avertissement signale des heuristiques
    non portées, pas un domaine parfait.
    """
    assert any(r["severity"] == "Warning" for r in results)


# --- Les contraintes attrapent les défauts transposés ----------------

def test_cas_de_reference_passe(results):
    """closeMatch à 0.75 : approximation honnête, correctement déclarée."""
    assert _sev(results, "RAP-OK") == set()
    assert _sev(results, "REGLE-OK") == set()


def test_exactmatch_faible_confiance_bloque(results):
    """Le défaut le plus coûteux : exactMatch autorise un agent à
    substituer un champ à l'autre sans prévenir. Jours calendrier
    contre jours ouvrables, transit inclus d'un seul côté.
    """
    assert "Violation" in _sev(results, "RAP-FAUX-EXACT")


def test_rapprochement_intra_systeme_bloque(results):
    assert "Violation" in _sev(results, "RAP-INTRA")


def test_rapprochement_sans_provenance_bloque(results):
    paths = {r["path"] for r in results if r["node"] == "RAP-ANONYME"}
    assert {"basis", "wasAttributedTo"} <= paths


def test_confiance_hors_bornes_bloque(results):
    assert "Violation" in _sev(results, "RAP-HORS-BORNES")


def test_concept_sans_systeme_bloque(results):
    """Un terme sans système est ininterprétable : capacité de quoi,
    mesurée comment, par qui ?
    """
    paths = {r["path"] for r in results if r["node"] == "CONCEPT-ORPHELIN"}
    assert "scopedTo" in paths


def test_regle_sans_source_bloque(results):
    assert "citation" in {r["path"] for r in results if r["node"] == "REGLE-SANS-SOURCE"}


def test_dates_incoherentes_bloquent(results):
    assert "Violation" in _sev(results, "REGLE-DATES")


# --- Signature des contraintes de noeud ------------------------------

def test_violations_de_noeud_sans_chemin(results):
    """Les contraintes SHACL-SPARQL portent sur le noeud entier, donc le
    rapport affiche '-' au lieu d'un nom de champ. Même signature que
    dans le domaine SST : c'est le même moteur.
    """
    for node in ("RAP-FAUX-EXACT", "RAP-INTRA", "REGLE-DATES"):
        assert None in [r["path"] for r in results if r["node"] == node]


def test_compte_total(results):
    """Verrou de régression du second domaine."""
    v = sum(1 for r in results if r["severity"] == "Violation")
    w = sum(1 for r in results if r["severity"] == "Warning")
    assert (v, w) == (8, 1)
