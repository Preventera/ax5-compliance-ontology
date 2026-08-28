"""
Tests des shapes SHACL.

PRINCIPE
On ne teste pas que le graphe est valide — il ne l'est pas, et c'est voulu.
On teste que les CONTRAINTES ATTRAPENT CE QU'ELLES DOIVENT ATTRAPER.

Le jeu de données contient des défauts délibérés qui servent de cas de test
négatifs. Une shape trop permissive laisse passer un défaut connu et le test
échoue. C'est ainsi qu'on empêche une régression silencieuse d'un contrat de
données au fil des versions de l'ontologie.
"""
import pathlib
import pytest
from rdflib import Graph, Namespace
from pyshacl import validate

ROOT = pathlib.Path(__file__).parent.parent
SH = Namespace("http://www.w3.org/ns/shacl#")
EX = "https://agenticx5.com/data/"


@pytest.fixture(scope="module")
def report():
    data = Graph()
    data.parse(ROOT / "ontology/ax5-compliance.ttl", format="turtle")
    data.parse(ROOT / "data/instances.ttl", format="turtle")

    shapes = Graph()
    shapes.parse(ROOT / "shapes/ax5-shapes.ttl", format="turtle")

    _, report_graph, _ = validate(
        data_graph=data, shacl_graph=shapes,
        inference="none", advanced=True,
        allow_warnings=True, allow_infos=True,
    )
    return report_graph


def findings(report, severity):
    out = []
    for r in report.subjects(None, SH.ValidationResult):
        if str(report.value(r, SH.resultSeverity)).endswith(severity):
            out.append(str(report.value(r, SH.focusNode)))
    return out


def test_ontology_parses():
    g = Graph()
    g.parse(ROOT / "ontology/ax5-compliance.ttl", format="turtle")
    assert len(g) > 50


def test_shapes_parse():
    g = Graph()
    g.parse(ROOT / "shapes/ax5-shapes.ttl", format="turtle")
    assert len(g) > 50


def test_concept_without_jurisdiction_is_rejected(report):
    """Un concept juridictionnel hors juridiction n'a aucun sens légal."""
    assert EX + "CPT-ORPHAN-Something" in findings(report, "Violation")


def test_weak_exact_match_is_rejected(report):
    """Politique : exactMatch exige une confiance >= 0.95. SHACL-SPARQL."""
    assert EX + "MAP-004" in findings(report, "Violation")


def test_intra_jurisdiction_mapping_is_rejected(report):
    """Un mapping traverse deux régimes par définition. SHACL-SPARQL."""
    assert EX + "MAP-005" in findings(report, "Violation")


def test_unattributed_mapping_is_rejected(report):
    """Une assertion sans base ni auteur n'est pas auditable."""
    assert EX + "MAP-006" in findings(report, "Violation")


def test_requirement_without_citation_is_rejected(report):
    """Une obligation non citable est inutilisable en conformité."""
    assert EX + "REQ-UK-CS-RiskAssess" in findings(report, "Violation")


def test_missing_hazard_is_warning_not_violation(report):
    """
    Décision d'architecte : les sources réglementaires sont incomplètes.
    Bloquer l'ingestion coûterait plus cher que tolérer le trou et le suivre.
    """
    node = EX + "REQ-INT-45001-Consult"
    assert node in findings(report, "Warning")
    assert node not in findings(report, "Violation")


def test_expected_violation_count(report):
    """
    Verrou de régression. Si ce chiffre bouge sans changement intentionnel
    des shapes ou des données, c'est qu'un contrat a dérivé.
    """
    assert len(findings(report, "Violation")) == 6


def test_competency_queries_all_return(report):
    """Les questions de compétence doivent toutes s'exécuter."""
    import sys
    sys.path.insert(0, str(ROOT / "queries"))
    import competency
    for title, _, q in competency.QUERIES:
        rows = list(competency.g.query(q))
        assert rows is not None, f"query failed: {title}"
