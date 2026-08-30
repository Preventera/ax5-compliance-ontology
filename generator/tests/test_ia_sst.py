"""
Tests du domaine IA × SST.

CE QUE CE DOMAINE A APPORTÉ AU GÉNÉRATEUR
-----------------------------------------
Troisième portage, deux défauts réels découverts :

1. `_sparql_cross_field` ne savait pas exprimer une condition
   d'ABSENCE dans la clause `alors`. Il liait la variable puis
   filtrait, ce qui signalait exactement l'inverse de la règle voulue :
   les applications QUI ONT un encadrement, au lieu de celles qui n'en
   ont pas. Corrigé par un FILTER NOT EXISTS.

2. La sévérité s'appliquait au bloc de propriété entier. Un champ
   dégradé en avertissement voyait aussi ses BORNES dégradées. Or
   « peut légitimement être absent » et « peut légitimement valoir
   n'importe quoi » sont deux affirmations différentes : un rang de
   hiérarchie des contrôles peut manquer, mais un rang de 7 est
   impossible. Corrigé par l'émission d'un second bloc qui garde la
   barrière dure sur les valeurs.

Les deux défauts existaient depuis le premier domaine. Aucun banc
d'essai ne les avait exercés. C'est l'argument pour porter un
générateur sur un domaine qu'on n'a pas conçu pour lui.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import SH
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "ia-sst.yml"
FIXTURE = ROOT / "tests" / "fixture_iasst.ttl"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("generated_iasst")
    subprocess.run(
        [sys.executable, str(ROOT / "generate.py"), str(SPEC), "--out", str(out)],
        check=True, cwd=ROOT,
    )
    return out


@pytest.fixture(scope="module")
def results(generated):
    data = Graph().parse(FIXTURE, format="turtle")
    shapes = Graph().parse(generated / "shapes" / "iasst-shapes.ttl", format="turtle")
    onto = Graph().parse(generated / "ontology" / "iasst.ttl", format="turtle")
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


def _paths(results, node):
    return {r["path"] for r in results if r["node"] == node}


# --- RDF valide sur un troisième domaine -----------------------------

def test_ontologie_parse(generated):
    assert len(Graph().parse(generated / "ontology" / "iasst.ttl", format="turtle")) > 0


def test_shapes_parsent(generated):
    assert len(Graph().parse(generated / "shapes" / "iasst-shapes.ttl", format="turtle")) > 0


# --- LE TEST CENTRAL : le niveau de décision porte le risque juridique

def test_decision_individuelle_sans_encadrement_bloque(results):
    """Le cœur du modèle.

    `APP-EPI-Nominatif` emploie la MÊME technique, vise le MÊME danger
    et couvre le MÊME secteur que `APP-EPI-Anonyme`. La seule différence
    est le niveau de décision : elle identifie le travailleur et alimente
    son évaluation de conformité.

    C'est du profilage sous la Loi 25 et un système à haut risque sous
    l'annexe III de l'AI Act. Sans encadrement cité, le référentiel
    présenterait cette application comme banale.

    Même mot, obligations différentes — le motif de l'ontologie de
    conformité, transposé d'un axe géographique à un axe décisionnel.
    """
    assert "Violation" in _sev(results, "APP-EPI-Nominatif")


def test_alerte_anonyme_passe(results):
    """La version anonyme de la même technique ne déclenche rien.

    Si ce test échoue en même temps que le précédent, la contrainte
    bloque sur la technique et non sur le niveau de décision — elle
    manquerait alors tout l'intérêt du modèle.
    """
    assert _sev(results, "APP-EPI-Anonyme") == set()


def test_encadrement_hors_regime_bloque(results):
    """Application encadrée au Québec citant l'AI Act européen.

    La preuve exige de traverser deux arcs et de comparer les régimes
    trouvés au bout : ni le sujet ni aucune de ses propriétés directes
    ne porte l'erreur.
    """
    assert "Violation" in _sev(results, "APP-Proximite")
    assert None in _paths(results, "APP-Proximite")


# --- Les barrières dures du référentiel ------------------------------

def test_risque_non_documente_bloque(results):
    """Un référentiel qui ne recense que les succès n'est pas crédible."""
    assert "risqueDocumente" in _paths(results, "APP-NLP-Codage")


def test_sans_provenance_bloque(results):
    assert {"basis", "wasAttributedTo"} <= _paths(results, "APP-Predictif-Anonyme")


def test_genre_accident_sans_regime_bloque(results):
    """Un code OIIC hors de son régime n'a pas de sens : la nomenclature
    adaptée du Québec n'est pas celle de l'ESAW européen.
    """
    assert "scopedTo" in _paths(results, "GA-ORPHELIN")


# --- Les trous légitimes restent des avertissements -------------------

def test_application_transversale_avertit_sans_bloquer(results):
    """La détection de fatigue vaut pour le transport, la construction
    et les mines. Aucun genre d'accident codé ne lui correspond non
    plus — la fatigue est un facteur, pas un événement.

    Bloquer forcerait un choix arbitraire ou trente fiches identiques.
    """
    sev = _sev(results, "APP-Fatigue")
    assert sev == {"Warning"}
    assert {"appliesToSector", "viseGenreAccident"} <= _paths(results, "APP-Fatigue")


def test_technique_sans_lexique_avertit(results):
    assert _sev(results, "ModelesPredictifs") == {"Warning"}


def test_surveillance_hors_hierarchie_passe(results):
    """La surveillance et l'amélioration ne se situent pas dans la
    hiérarchie des contrôles : ce ne sont pas des mesures de maîtrise.
    Le rang vide est correct, pas fautif.
    """
    assert _sev(results, "INT-Surveillance") == set()


# --- La régression corrigée par ce domaine ---------------------------

def test_borne_reste_dure_malgre_presence_degradee(results):
    """Régression n° 2.

    `rangHierarchie` peut légitimement être absent, donc sa présence est
    un avertissement. Mais un rang de 7 est impossible — la hiérarchie
    des contrôles en compte cinq.

    Avant correction, la borne héritait de la sévérité de présence et
    sortait en avertissement. « Peut être absent » et « peut valoir
    n'importe quoi » sont deux affirmations différentes.
    """
    assert "Violation" in _sev(results, "INT-INVALIDE")
    assert "rangHierarchie" in _paths(results, "INT-INVALIDE")


def test_au_moins_un_signal_doux(results):
    assert any(r["severity"] == "Warning" for r in results)


def test_compte_total(results):
    """Verrou de régression du troisième domaine."""
    v = sum(1 for r in results if r["severity"] == "Violation")
    w = sum(1 for r in results if r["severity"] == "Warning")
    assert (v, w) == (7, 3)
