#!/usr/bin/env python3
"""
AX5 — Les trois autres formes SPARQL, une par consommateur.

RAPPEL MÉTHODOLOGIQUE
Un graphe de connaissances est un magasin, pas un format de réponse.
La forme de la requête se choisit selon ce que le consommateur doit
faire du résultat :

  SELECT    un humain qui lit          -> un tableau
  ASK       un agent avant d'agir      -> un booléen
  CONSTRUCT un système en aval         -> un sous-graphe réutilisable
  DESCRIBE  une interface              -> la fiche d'une ressource

queries/competency.py couvre SELECT. Ce fichier couvre les trois autres.

Usage:  python3 queries/forms.py
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

("CQ-9  ASK — un agent peut-il substituer ce concept à l'autre sans avertir ?",
 """
 La barrière, exprimée formellement.

 exactMatch n'est pas une observation sur le monde : c'est une
 PERMISSION accordée à un agent de remplacer un concept par un autre
 sans prévenir personne. Une permission se vérifie avant d'agir, pas
 après.

 Trois conditions cumulatives : relation exactMatch, confiance au
 moins égale à 0,95, revue humaine effectuée.

 Sur ce jeu de données la réponse est FALSE, et c'est le comportement
 voulu : MAP-004 est bien un exactMatch, mais à 0,55 et en
 machine-proposed. La barrière tient.

 Un agent n'a pas besoin d'un tableau. Il a besoin d'un feu vert ou
 rouge. D'où ASK plutôt que SELECT.
 """,
 PREFIX + """
 ASK {
     ?m a ax5:ConceptMapping ;
        ax5:mapsFrom ?a ;
        ax5:mapsTo ?b ;
        ax5:mappingRelation skos:exactMatch ;
        ax5:confidence ?c ;
        ax5:reviewStatus "human-reviewed" .
     ?a skos:prefLabel "Lésion professionnelle déclarable"@fr .
     FILTER(?c >= 0.95)
 }
 """),

("CQ-10  CONSTRUCT — le paquet de preuve d'une correspondance non revue",
 """
 Un dossier d'audit n'est pas un tableau : c'est un sous-graphe.

 Un tableau se lit puis se jette. Un sous-graphe RDF se recharge, se
 revérifie, se transmet à un régulateur qui l'interroge avec ses
 propres requêtes. C'est la différence entre une capture d'écran et
 une preuve.

 Ce CONSTRUCT extrait tout ce qu'un auditeur doit voir sur une
 correspondance proposée par une machine : la relation, la confiance,
 la base invoquée, le statut de revue, l'agent auteur — et les deux
 concepts avec leurs seuils, pour que l'écart soit visible sans avoir
 à retourner au graphe complet.

 Filtré sur reviewStatus = machine-proposed : ce sont précisément les
 affirmations qui ne doivent fonder aucune décision engageante.
 """,
 PREFIX + """
 CONSTRUCT {
     ?m  a ax5:ConceptMapping ;
         ax5:mapsFrom ?a ;
         ax5:mapsTo ?b ;
         ax5:mappingRelation ?rel ;
         ax5:confidence ?c ;
         ax5:basis ?basis ;
         ax5:reviewStatus ?st ;
         prov:wasAttributedTo ?agent .
     ?a  skos:prefLabel ?la ; ax5:threshold ?ta ; ax5:thresholdUnit ?ua .
     ?b  skos:prefLabel ?lb ; ax5:threshold ?tb ; ax5:thresholdUnit ?ub .
 }
 WHERE {
     ?m a ax5:ConceptMapping ;
        ax5:mapsFrom ?a ;
        ax5:mapsTo ?b ;
        ax5:mappingRelation ?rel ;
        ax5:confidence ?c ;
        ax5:basis ?basis ;
        ax5:reviewStatus ?st .
     OPTIONAL { ?m prov:wasAttributedTo ?agent }
     ?a skos:prefLabel ?la .
     ?b skos:prefLabel ?lb .
     OPTIONAL { ?a ax5:threshold ?ta . ?a ax5:thresholdUnit ?ua }
     OPTIONAL { ?b ax5:threshold ?tb . ?b ax5:thresholdUnit ?ub }
     FILTER(?st = "machine-proposed")
 }
 """),

("CQ-11  DESCRIBE — la fiche complète d'un concept juridictionnel",
 """
 Ce que l'inspecteur affiche, exprimé en SPARQL.

 DESCRIBE ne demande pas quelles propriétés on veut : il retourne ce
 que le magasin sait de la ressource. C'est la requête d'une interface
 qui ouvre une fiche sans savoir d'avance ce qu'elle contiendra.

 Le panneau inspecteur de l'explorateur fait exactement ça, en
 JavaScript sur des données embarquées. Le formuler en DESCRIBE, c'est
 nommer la sémantique derrière l'interface.

 Noter ce qui sort : le seuil de 1 et son unité « day away from work ».
 C'est la moitié du conflit que CQ-5 met en évidence — vu ici du côté
 d'un seul régime.
 """,
 PREFIX + """
 DESCRIBE ?concept
 WHERE {
     ?concept a ax5:JurisdictionalConcept ;
              skos:prefLabel "Lésion professionnelle déclarable"@fr .
 }
 """),
]


def run():
    for title, note, q in QUERIES:
        print("\n" + "=" * 78)
        print(title)
        print("=" * 78)
        print(note.strip("\n"))
        print("-" * 78)
        res = g.query(q)

        if res.type == "ASK":
            print("  ->", bool(res), "— la substitution n'est PAS autorisée"
                  if not bool(res) else "— substitution autorisée")

        elif res.type == "CONSTRUCT" or res.type == "DESCRIBE":
            out = res.graph
            print(f"  {len(out)} triplets produits\n")
            print("  " + out.serialize(format="turtle").replace("\n", "\n  ").rstrip())

        else:
            for row in res:
                print("  " + " | ".join(
                    f"{v}={row[v]}" for v in res.vars if row[v] is not None))
    print()


if __name__ == "__main__":
    run()
