#!/usr/bin/env python3
"""
AX5 — Validation SHACL du graphe de conformité.

Usage:  python3 validate.py
"""
import sys, pathlib
from rdflib import Graph
from pyshacl import validate

ROOT = pathlib.Path(__file__).parent

def load(*paths):
    g = Graph()
    for p in paths:
        g.parse(ROOT / p, format="turtle")
    return g

def main():
    data = load("ontology/ax5-compliance.ttl", "data/instances.ttl")
    shapes = load("shapes/ax5-shapes.ttl")

    print(f"Graphe de données : {len(data)} triplets")
    print(f"Shapes            : {len(shapes)} triplets\n")

    conforms, report_graph, report_text = validate(
        data_graph=data,
        shacl_graph=shapes,
        inference="none",          # pas d'inférence : on valide les faits tels quels
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,       # les Warnings n'invalident pas le graphe
        meta_shacl=False,
        advanced=True,             # nécessaire pour SHACL-SPARQL
        debug=False,
    )

    # Extraction structurée du rapport
    from rdflib.namespace import Namespace
    SH = Namespace("http://www.w3.org/ns/shacl#")

    results = []
    for r in report_graph.subjects(None, SH.ValidationResult):
        sev = report_graph.value(r, SH.resultSeverity)
        node = report_graph.value(r, SH.focusNode)
        msg = report_graph.value(r, SH.resultMessage)
        path = report_graph.value(r, SH.resultPath)
        results.append((
            str(sev).split("#")[-1],
            str(node).split("/")[-1],
            str(path).split("#")[-1] if path else "-",
            str(msg),
        ))

    violations = [r for r in results if r[0] == "Violation"]
    warnings = [r for r in results if r[0] == "Warning"]

    print("=" * 78)
    print(f"VIOLATIONS : {len(violations)}     WARNINGS : {len(warnings)}")
    print("=" * 78)

    for sev, node, path, msg in sorted(violations):
        print(f"\n[{sev}] {node}   (propriété : {path})")
        print(f"   -> {msg}")

    for sev, node, path, msg in sorted(warnings):
        print(f"\n[{sev}] {node}   (propriété : {path})")
        print(f"   -> {msg}")

    print("\n" + "=" * 78)
    print("Conforme (violations seulement) :", len(violations) == 0)
    print("=" * 78)

    # Métrique de plateforme : taux de violation, à suivre dans le temps.
    n_req = len(set(data.subjects(None, None)))
    print(f"\nMétrique suivable : {len(violations)} violations / {n_req} sujets")

    return 0

if __name__ == "__main__":
    sys.exit(main())
