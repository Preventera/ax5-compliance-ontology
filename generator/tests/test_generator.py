"""
Tests du générateur.

CE QU'ON TESTE VRAIMENT
-----------------------
On ne teste pas que le générateur « produit du RDF ». N'importe quel
gabarit fait ça. On teste que les shapes produites ATTRAPENT les défauts
qu'on connaît — et qu'elles laissent passer la donnée valide.

Un générateur qui produit des shapes trop permissives est pire
qu'inutile : il donne une fausse assurance de qualité.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import SH
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "sst-quebec.yml"
FIXTURE = ROOT / "tests" / "fixture_defauts.ttl"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("generated")
    subprocess.run(
        [sys.executable, str(ROOT / "generate.py"), str(SPEC), "--out", str(out)],
        check=True, cwd=ROOT,
    )
    return out


@pytest.fixture(scope="module")
def results(generated):
    data = Graph().parse(FIXTURE, format="turtle")
    shapes = Graph().parse(generated / "shapes" / "sst-shapes.ttl", format="turtle")
    onto = Graph().parse(generated / "ontology" / "sst.ttl", format="turtle")
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


# --- Le RDF produit est bien formé -----------------------------------

def test_ontologie_parse(generated):
    g = Graph().parse(generated / "ontology" / "sst.ttl", format="turtle")
    assert len(g) > 0


def test_shapes_parsent(generated):
    g = Graph().parse(generated / "shapes" / "sst-shapes.ttl", format="turtle")
    assert len(g) > 0


# --- Le générateur exerce son jugement -------------------------------

def test_champ_obligatoire_degrade_en_warning(generated):
    """addressesHazard est déclaré obligatoire dans le spec.

    Le générateur refuse d'en faire une barrière dure : de la donnée
    légitime (les exigences de système de gestion) échouerait. C'est
    le seul endroit du générateur qui contredit l'auteur du spec, et
    il doit dire pourquoi.
    """
    rapport = (generated / "DECISIONS.md").read_text(encoding="utf-8")
    assert "addressesHazard" in rapport
    assert "TEST 2" in rapport


def test_rapport_de_decisions_existe(generated):
    assert (generated / "DECISIONS.md").exists()


# --- Les shapes attrapent les défauts connus -------------------------

def test_cas_de_reference_passe(results):
    """La donnée valide ne doit RIEN déclencher. Sinon on rejette du vrai."""
    assert _sev(results, "OBL-OK") == set()


def test_citation_manquante_bloque(results):
    assert "Violation" in _sev(results, "OBL-SANS-CITATION")


def test_concept_sans_juridiction_bloque(results):
    assert "Violation" in _sev(results, "CONCEPT-ORPHELIN")


def test_danger_manquant_avertit_sans_bloquer(results):
    sev = _sev(results, "OBL-SYSTEME")
    assert sev == {"Warning"}, "Ne doit pas bloquer : donnée légitime."


def test_dates_incoherentes_bloquent(results):
    """Règle croisée : deux champs du même noeud, donc SHACL-SPARQL."""
    assert "Violation" in _sev(results, "OBL-DATES-INVERSEES")


def test_exactmatch_faible_confiance_bloque(results):
    assert "Violation" in _sev(results, "MAP-FAIBLE")


def test_correspondance_intra_regime_bloque(results):
    """La preuve exige de traverser deux arcs et de comparer les bouts."""
    assert "Violation" in _sev(results, "MAP-INTRA")


def test_confiance_hors_bornes_bloque(results):
    assert "Violation" in _sev(results, "MAP-HORS-BORNES")


# --- Signature du rapport --------------------------------------------

def test_violations_de_noeud_sans_chemin(results):
    """Les contraintes SHACL-SPARQL portent sur le NOEUD, pas un chemin.

    Le rapport affiche donc '-' au lieu d'un nom de champ. Cette
    signature dans la sortie indique le type de contrainte qui a tiré.
    """
    for node in ("MAP-FAIBLE", "MAP-INTRA", "OBL-DATES-INVERSEES"):
        paths = [r["path"] for r in results if r["node"] == node]
        assert None in paths, f"{node} devrait produire une violation de noeud"


def test_compte_total(results):
    """Verrou de régression.

    Si ce test échoue après une modification du générateur, la question
    n'est pas « comment le faire passer » — c'est « quelle contrainte
    ai-je affaiblie sans m'en rendre compte ».
    """
    v = sum(1 for r in results if r["severity"] == "Violation")
    w = sum(1 for r in results if r["severity"] == "Warning")
    assert (v, w) == (6, 1)
