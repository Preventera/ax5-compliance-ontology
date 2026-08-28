#!/usr/bin/env python3
"""
AX5 — Les questions de compétence, exprimées en SPARQL.

RAPPEL MÉTHODOLOGIQUE
Une ontologie ne se conçoit pas en listant des concepts. Elle se conçoit
en écrivant les questions auxquelles elle doit répondre. Ces questions
servent trois fois :
  1. elles délimitent la portée du modèle
  2. elles arbitrent les débats de modélisation
  3. elles DEVIENNENT le jeu d'évaluation des agents

C'est le point 3 que presque personne ne fait, et c'est celui qui relie
l'ontologie aux évaluateurs.

Usage:  python3 queries/competency.py
"""
import pathlib
from rdflib import Graph

ROOT = pathlib.Path(__file__).parent.parent
g = Graph()
g.parse(ROOT / "ontology/ax5-compliance.ttl", format="turtle")
g.parse(ROOT / "data/instances.ttl", format="turtle")

PREFIX = """
PREFIX ax5:  <https://agenticx5.com/ont/compliance#>
PREFIX ex:   <https://agenticx5.com/data/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

QUERIES = [

("CQ-1  Quelles exigences s'appliquent à une tâche, sur un site donné ?",
 """
 Traversée sur trois arcs : activité -> danger -> exigence, filtrée par
 la juridiction du site. C'est l'équivalent conformité d'une explosion
 de nomenclature.
 """,
 PREFIX + """
 SELECT ?hazard ?requirement ?citation ?jurisdiction
 WHERE {
     ex:ACT-TankEntry ax5:presentsHazard ?haz .
     ?req ax5:addressesHazard ?haz ;
          ax5:citation ?citation ;
          ax5:statedIn ?instrument .
     ?instrument ax5:hasJurisdiction ?jur .
     ex:SITE-Bromont ax5:locatedIn ?jur .
     ?haz rdfs:label ?hazard .
     ?req rdfs:label ?requirement .
     ?jur rdfs:label ?jurisdiction .
 }
 ORDER BY ?hazard
 """),

("CQ-2  Chemin de propriété : danger -> mesure -> exigence, en un saut",
 """
 Les chemins de propriété (ax5:mitigatedBy/ax5:mandatedBy) sont la
 manière SPARQL de faire de la traversée. C'est le mécanisme qu'il faut
 connaître : c'est ce qui sert au pegging et à l'explosion de BOM.
 """,
 PREFIX + """
 SELECT ?hazard ?requirement
 WHERE {
     ?haz ax5:mitigatedBy/ax5:mandatedBy ?req .
     ?haz rdfs:label ?hazard .
     ?req rdfs:label ?requirement .
 }
 """),

("CQ-3  Un concept US donné : quels équivalents au Québec, et à quel degré ?",
 """
 La question centrale du multi-juridictionnel. Noter que la réponse
 n'est JAMAIS un simple oui/non : elle porte un type de relation, une
 confiance, une base et un statut de revue.
 """,
 PREFIX + """
 SELECT ?source ?relation ?confidence ?status ?target ?basis
 WHERE {
     ?m a ax5:ConceptMapping ;
        ax5:mapsFrom ?a ; ax5:mapsTo ?b ;
        ax5:mappingRelation ?rel ;
        ax5:confidence ?confidence ;
        ax5:reviewStatus ?status .
     OPTIONAL { ?m ax5:basis ?basis }
     ?a ax5:scopedTo ex:JUR-QC .
     ?b ax5:scopedTo ex:JUR-US .
     ?a skos:prefLabel ?source .
     ?b skos:prefLabel ?target .
     BIND(REPLACE(STR(?rel), "^.*core#", "") AS ?relation)
 }
 ORDER BY DESC(?confidence)
 """),

("CQ-4  ANGLE MORT : quels concepts ancres n'ont AUCUN équivalent au UK ?",
 """
 *** LA REQUÊTE LA PLUS IMPORTANTE DU JEU ***

 Elle trouve les TROUS, pas les correspondances. C'est ce qu'un agent
 doit pouvoir dire : « je n'ai pas de réponse pour ce régime », plutôt
 que d'inventer une équivalence plausible.

 Techniquement : NOT EXISTS. Conceptuellement : c'est ton produit
 Blindspot, exprimé formellement.
 """,
 PREFIX + """
 SELECT ?anchor ?coveredJurisdictions
 WHERE {
     ?anc a ax5:AnchorConcept ; skos:prefLabel ?anchor .
     FILTER NOT EXISTS {
         ?c ax5:anchoredTo ?anc ; ax5:scopedTo ex:JUR-UK .
     }
     {
         SELECT ?anc (COUNT(DISTINCT ?j) AS ?coveredJurisdictions)
         WHERE {
             ?anc a ax5:AnchorConcept .
             OPTIONAL { ?cc ax5:anchoredTo ?anc ; ax5:scopedTo ?j }
         }
         GROUP BY ?anc
     }
 }
 """),

("CQ-5  CONFLIT DE SEUIL : mêmes ancres, seuils divergents",
 """
 Le cas où deux régimes couvrent le même concept mais comptent
 différemment. Un agent qui ignore ça produit une réponse fluide et
 fausse dans l'une des deux juridictions.
 """,
 PREFIX + """
 SELECT ?anchor ?labelA ?thresholdA ?unitA ?labelB ?thresholdB ?unitB
 WHERE {
     ?a ax5:anchoredTo ?anc ; ax5:threshold ?thresholdA ;
        ax5:thresholdUnit ?unitA ; skos:prefLabel ?labelA ; ax5:scopedTo ?ja .
     ?b ax5:anchoredTo ?anc ; ax5:threshold ?thresholdB ;
        ax5:thresholdUnit ?unitB ; skos:prefLabel ?labelB ; ax5:scopedTo ?jb .
     ?anc skos:prefLabel ?anchor .
     FILTER (STR(?ja) < STR(?jb))
     FILTER (?unitA != ?unitB)
 }
 """),

("CQ-6  BITEMPOREL : quelles exigences étaient en vigueur le 2010-05-01 ?",
 """
 Axe de VALIDITÉ. Répond à « qu'est-ce qui était vrai à cette date ».
 Noter que REQ-QC-Ancienne apparaît ici mais pas aujourd'hui.
 """,
 PREFIX + """
 SELECT ?requirement ?citation ?validFrom ?validTo
 WHERE {
     ?req a ax5:Requirement ;
          rdfs:label ?requirement ;
          ax5:citation ?citation ;
          ax5:validFrom ?validFrom .
     OPTIONAL { ?req ax5:validTo ?validTo }
     FILTER (?validFrom <= "2010-05-01"^^xsd:date)
     FILTER (!BOUND(?validTo) || ?validTo >= "2010-05-01"^^xsd:date)
 }
 ORDER BY ?validFrom
 """),

("CQ-7  GOUVERNANCE : quelles assertions machine n'ont jamais été revues ?",
 """
 File d'attente de revue humaine. Dans un système agentique, c'est la
 barrière : tout ce qui est proposé par une machine et non revu est
 utilisable en lecture mais ne doit pas fonder une décision engageante.
 """,
 PREFIX + """
 SELECT ?mapping ?status ?confidence ?agent
 WHERE {
     ?m a ax5:ConceptMapping ;
        rdfs:label ?mapping ;
        ax5:reviewStatus ?status ;
        ax5:confidence ?confidence .
     OPTIONAL { ?m prov:wasAttributedTo ?ag . ?ag rdfs:label ?agent }
     FILTER (?status IN ("machine-proposed", "draft"))
 }
 ORDER BY DESC(?confidence)
 """),

("CQ-8  COUVERTURE : combien de régimes couvrent chaque ancre ?",
 """
 Métrique de plateforme. Agrégation simple, mais c'est le genre de
 chiffre qu'on suit dans le temps pour savoir si le modèle progresse.
 """,
 PREFIX + """
 SELECT ?anchor (COUNT(DISTINCT ?jur) AS ?regimes)
        (GROUP_CONCAT(DISTINCT ?jname; separator=", ") AS ?list)
 WHERE {
     ?anc a ax5:AnchorConcept ; skos:prefLabel ?anchor .
     OPTIONAL {
         ?c ax5:anchoredTo ?anc ; ax5:scopedTo ?jur .
         ?jur rdfs:label ?jl .
     }
     BIND(COALESCE(?jl, "— none —") AS ?jname)
 }
 GROUP BY ?anchor
 ORDER BY ?regimes
 """),
]


def run():
    for title, note, q in QUERIES:
        print("\n" + "=" * 78)
        print(title)
        print("=" * 78)
        print(note.strip())
        print("-" * 78)
        rows = list(g.query(q))
        if not rows:
            print("  (aucun résultat)")
            continue
        for row in rows:
            parts = []
            for var, val in zip(row.labels, row):
                v = str(val) if val is not None else "—"
                if len(v) > 60:
                    v = v[:57] + "..."
                parts.append(f"{var}={v}")
            print("  " + " | ".join(parts))
    print("\n" + "=" * 78)
    print(f"{len(QUERIES)} questions de compétence exécutées.")
    print("=" * 78)


if __name__ == "__main__":
    run()
