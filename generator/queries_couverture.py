#!/usr/bin/env python3
"""
REQUÊTES DE COUVERTURE
======================

Les questions qu'aucun système de gestion SST ne peut poser, parce que
son architecture ne le permet pas.

Toutes reposent sur la même bascule : la revendication de couverture est
une ENTITÉ, pas un lien. Une procédure ne satisfait pas une obligation —
quelqu'un AFFIRME qu'elle la satisfait, sur une base, à une date, avec un
statut de revue.

Un lien ne porte rien de tout ça, et surtout : un lien ne peut pas être
faux. Une affirmation, si.

Usage :
    python queries/couverture.py [--data data/instances.ttl]
"""

import argparse
import sys
from pathlib import Path

from rdflib import Graph

PREFIX = """
PREFIX sst: <https://agenticx5.com/ont/sst#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

QUERIES = [

 ("CQ-49", "Quelles obligations ne sont couvertes par AUCUN document interne ?",
  """La question qui justifie le projet à elle seule.

  Un SGSST peut lister les procédures qui existent. Il ne peut pas
  lister celles qui manquent, parce qu'il n'a aucun modèle de ce qui
  DEVRAIT exister — il ne connaît que ce qu'on lui a saisi.

  Le renversement : on n'interroge pas les procédures, on interroge les
  obligations, et on garde celles vers lesquelles rien ne pointe.""",
  PREFIX + """
    SELECT ?obligation ?citation ?regime
    WHERE {
      ?obligation a sst:Obligation ;
                  sst:citation ?citation ;
                  sst:statedIn/sst:hasJurisdiction/sst:nom ?regime .
      FILTER NOT EXISTS { ?rev sst:couvreObligation ?obligation }
    }
    ORDER BY ?regime ?citation
  """),

 ("CQ-50", "Quels documents internes ne couvrent aucune obligation identifiée ?",
  """La question miroir, et elle dérange davantage.

  Un document qui ne prétend rien mettre en oeuvre existe pour une
  raison qu'on a oubliée. Ce n'est pas nécessairement une erreur — mais
  personne ne peut dire pourquoi il est là, ni ce qui se passe si on le
  supprime.""",
  PREFIX + """
    SELECT ?document ?reference ?titre
    WHERE {
      ?document a sst:DocumentInterne ;
                sst:reference ?reference ;
                sst:titre ?titre .
      FILTER NOT EXISTS { ?rev sst:parDocument ?document }
    }
    ORDER BY ?reference
  """),

 ("CQ-51", "Quelles couvertures reposent sur une affirmation non revue ?",
  """La différence entre « nous pensons être conformes » et « quelqu'un
  a vérifié ». Une extraction automatique qui déclare une couverture
  complète produit exactement l'assurance que personne n'a validée.""",
  PREFIX + """
    SELECT ?rev ?degre ?statut ?auteur ?citation
    WHERE {
      ?rev a sst:RevendicationCouverture ;
           sst:degreCouverture ?degre ;
           sst:reviewStatus ?statut ;
           sst:wasAttributedTo ?auteur ;
           sst:couvreObligation/sst:citation ?citation .
      FILTER (?statut != "human-reviewed")
    }
    ORDER BY ?citation
  """),

 ("CQ-52", "Quelles obligations n'ont qu'une couverture PARTIELLE ?",
  """Le trou le plus insidieux : ni absent, ni complet.

  Une couverture partielle assumée est saine — elle dit ce qu'elle ne
  fait pas. Le danger est qu'elle soit lue comme une couverture tout
  court, et que personne ne se demande ce qui reste découvert.""",
  PREFIX + """
    SELECT ?citation ?document ?base
    WHERE {
      ?rev a sst:RevendicationCouverture ;
           sst:degreCouverture ?degre ;
           sst:basis ?base ;
           sst:couvreObligation/sst:citation ?citation ;
           sst:parDocument/sst:reference ?document .
      FILTER (?degre != "complete")
      FILTER NOT EXISTS {
        ?autre sst:couvreObligation/sst:citation ?citation ;
               sst:degreCouverture "complete" .
      }
    }
    ORDER BY ?citation
  """),

 ("CQ-53", "Taux de couverture par régime",
  """La métrique que le trou de couverture rend possible.

  Elle ne dit pas « nous sommes conformes à 80 % » — ça n'aurait aucun
  sens. Elle dit : sur les obligations que nous avons encodées, 80 %
  ont au moins un document qui prétend les couvrir. Le reste est un
  angle mort documenté.""",
  PREFIX + """
    SELECT ?regime (COUNT(DISTINCT ?obl) AS ?total)
                   (COUNT(DISTINCT ?couverte) AS ?couvertes)
    WHERE {
      ?obl a sst:Obligation ;
           sst:statedIn/sst:hasJurisdiction/sst:nom ?regime .
      OPTIONAL {
        ?rev sst:couvreObligation ?obl .
        BIND(?obl AS ?couverte)
      }
    }
    GROUP BY ?regime
    ORDER BY ?regime
  """),

 ("CQ-54", "Quelles obligations ont changé depuis la revue de leur couverture ?",
  """La question bitemporelle de la couverture.

  Une procédure revue en 2024 peut couvrir un article modifié en 2026.
  Le document n'a pas bougé, la revendication non plus — mais elle
  porte désormais sur un texte qui n'existe plus sous cette forme.

  C'est le mécanisme d'alerte de changement réglementaire, et il ne
  demande qu'une comparaison de dates.""",
  PREFIX + """
    SELECT ?citation ?obligationSaisie ?couvertureSaisie ?document
    WHERE {
      ?rev a sst:RevendicationCouverture ;
           sst:recordedAt ?couvertureSaisie ;
           sst:couvreObligation ?obl ;
           sst:parDocument/sst:reference ?document .
      ?obl sst:citation ?citation ;
           sst:recordedAt ?obligationSaisie .
      FILTER (?obligationSaisie > ?couvertureSaisie)
    }
    ORDER BY ?citation
  """),
]


def run(data_path: Path) -> int:
    g = Graph()
    g.parse(data_path, format="turtle")
    print("=" * 70)
    print(f"  Graphe : {data_path}  —  {len(g)} triplets")
    print("=" * 70)

    for code, question, pourquoi, q in QUERIES:
        print(f"\n{'─' * 70}")
        print(f"{code} — {question}")
        print("─" * 70)
        for ligne in pourquoi.strip().split("\n"):
            print(f"  {ligne.strip()}")
        print()
        try:
            rows = list(g.query(q))
        except Exception as e:
            print(f"  [erreur] {e}")
            continue
        if not rows:
            print("  → Aucun résultat.")
            print("    Sur une question de trou, c'est la BONNE réponse :")
            print("    tout est couvert. Sur un graphe vide, c'est un piège —")
            print("    le système ne connaît que ce qu'on lui a donné.")
            continue
        for r in rows:
            vals = [str(v).split("#")[-1] if v else "—" for v in r]
            print("  → " + "  |  ".join(vals))
        print(f"\n  {len(rows)} résultat(s).")

    print(f"\n{'=' * 70}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Requêtes de couverture AX5")
    ap.add_argument("--data", default="data/instances.ttl")
    args = ap.parse_args()
    p = Path(args.data)
    if not p.exists():
        print(f"Fichier introuvable : {p}", file=sys.stderr)
        return 1
    return run(p)


if __name__ == "__main__":
    sys.exit(main())
