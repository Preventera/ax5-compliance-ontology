---
name: ontox5-rendu
description: Doctrine de rendu pour l'explorateur AX5 et toute vue produite à partir de l'ontologie de conformité (ax5-explorer, exports, captures de démonstration). À charger avant toute génération ou modification d'une surface visuelle du dépôt ax5-onto. Fixe les molettes de registre, les quatre états de couverture, et les règles vérifiables mécaniquement par tests/test_rendu_explorateur.py. Ne s'applique pas au TTL, aux shapes ni au générateur.
---

# Doctrine de rendu — OntoX5

Le modèle affirme qu'une correspondance est une fiche et non un trait,
parce qu'un trait ne s'audite pas. Une interface qui affiche cette fiche
comme un trait annule la décision de modélisation. Le rendu n'est donc
pas une couche cosmétique posée sur l'ontologie : c'est la dernière
étape où la thèse peut être trahie.

Cette doctrine est la contrepartie visuelle des shapes SHACL. Les shapes
disent ce qu'une donnée doit porter pour être admissible. Ce document dit
ce qu'un écran doit porter pour être admissible.

---

## 1. Les molettes

Quatre variables nommées. Toute règle des sections suivantes s'y réfère
par ce nom exact. Ne pas inventer d'alias.

| Molette | Échelle | Valeur OntoX5 |
|---|---|---|
| `VARIANCE` | 1 = grille stricte · 10 = composition libre | **2** |
| `MOUVEMENT` | 1 = statique · 10 = animation scénarisée | **1** |
| `DENSITE` | 1 = aéré · 10 = cockpit | **7** |
| `EXPLICITATION` | 1 = verdict seul · 10 = toute la chaîne de provenance visible | **9** |

`EXPLICITATION` est la molette propre à ce projet, et la seule qui ne se
règle pas vers le bas. Les trois autres se négocient ; celle-ci non.

**Justification des valeurs.** `VARIANCE` à 2 parce qu'une vue de
conformité tire son autorité de sa prévisibilité : deux régimes doivent
occuper deux colonnes identiques, sinon la comparaison est biaisée par la
mise en page. `MOUVEMENT` à 1 parce qu'un état qui bouge suggère un
calcul en cours ; or rien n'est calculé ici, tout est lu.
`DENSITE` à 7 parce que la valeur de l'écran est la juxtaposition, pas la
respiration.

**Table d'inférence.** Si un brief demande autre chose, ces valeurs se
déplacent ainsi, et seulement ainsi :

| Contexte du brief | VARIANCE | MOUVEMENT | DENSITE | EXPLICITATION |
|---|---|---|---|---|
| Explorateur public (défaut) | 2 | 1 | 7 | 9 |
| Capture de démonstration, 90 s | 3 | 2 | 6 | 9 |
| Impression / export PDF | 1 | 0 | 8 | 10 |
| Vue intégrée dans un agent | 1 | 0 | 5 | 10 |

Aucun contexte ne descend `EXPLICITATION` sous 9. Un écran qui affiche un
résultat de conformité sans sa provenance n'est pas une version simplifiée
de cet explorateur : c'est un autre produit, et un produit dangereux.

---

## 2. Les quatre états de couverture

C'est la règle centrale. Les revendications de couverture affichent des
absences, et trois absences différentes se ressemblent à l'écran alors
qu'elles n'ont pas les mêmes conséquences.

| État | Ce que la donnée dit | Ce que l'écran doit dire |
|---|---|---|
| `COUVERT` | Une assertion réifiée relie un document à l'obligation | Satisfait, avec le document et sa version |
| `COUVERT_RESERVE` | Assertion présente, mais confiance sous le seuil, ou statut proposé par machine | Satisfait sous réserve, avec le motif de la réserve |
| `LACUNE` | Obligation évaluée, aucune assertion trouvée | Trou de couverture réel |
| `NON_EVALUE` | Aucune donnée chargée pour cette obligation | Le système n'a pas regardé |

`LACUNE` et `NON_EVALUE` sont la paire qu'il ne faut jamais confondre. La
première engage le client, la seconde engage le corpus. Confondre les deux
produit soit une fausse alerte, soit une fausse assurance, et la fausse
assurance est la faute grave.

Chaque état porte **trois canaux indépendants** : un libellé textuel, une
forme ou un glyphe, et une couleur. Deux des trois doivent suffire. Le
canal couleur est toujours le canal redondant, jamais le canal porteur.

`NON_EVALUE` n'est pas un état neutre affiché en gris pâle. Le gris pâle
se lit comme « rien à signaler ». Il faut un glyphe explicite et un
libellé qui nomme l'ignorance du système, dans la langue de l'écran.

---

## 3. Règles falsifiables

Chaque règle est formulée pour qu'un test puisse la contredire. Une règle
qu'aucun test ne peut faire échouer n'a pas sa place ici.

**R1 — Aucun état porté par la couleur seule.** Tout élément signalant un
état de validation, de couverture, de confiance ou de revue porte au moins
deux canaux parmi libellé, glyphe, forme. Vérifiable : chaque nœud portant
une classe d'état contient du texte non vide ou un enfant marqué comme
glyphe.

**R2 — Le vide, le zéro et l'inconnu ne se ressemblent pas.** Trois rendus
distincts pour « aucun résultat », « valeur nulle mesurée » et « non
évalué ». Un tiret cadratin partout est une violation.

**R3 — Aucun compteur sans dénominateur, source et date.** « 12 violations »
est interdit. « 12 violations sur 47 obligations évaluées ·
tests/fixture_defauts.ttl · 2026-09-05 » est la forme minimale. Vérifiable :
tout nœud de compteur porte `data-denominator`, `data-source`, `data-asof`.

**R4 — La provenance est au premier niveau de lecture.** Base, auteur,
statut de revue et date d'une correspondance sont visibles sans survol,
sans clic, sans dépliant. `EXPLICITATION` = 9 signifie exactement cela.

**R5 — L'ancre n'est jamais présentée comme une réponse.** `AnchorConcept`
est typographiquement subordonné aux concepts juridictionnels : taille
inférieure ou égale, jamais en position de titre principal d'une fiche de
résultat. L'instinct de mise en page place le pivot au centre et en gros ;
c'est précisément l'erreur, parce que l'ancre n'a aucune force légale.

**R6 — `exactMatch` et `closeMatch` ne se ressemblent pas.** `exactMatch`
autorise un agent à substituer un concept à l'autre sans prévenir. Cette
autorisation doit être lisible comme telle, avec sa confiance affichée à
côté du seuil de 0,95.

**R7 — Machine et humain se distinguent sans interaction.** Une
correspondance proposée par machine et une correspondance revue par un
humain ne partagent aucun rendu. Pas de nuance de la même pastille.

**R8 — Le mot « conforme » est banni hors du lexique.** L'écran affiche ce
que la contrainte dit, pas un verdict : « satisfait la contrainte
`MAP-006` », pas « conforme ». Le pied de page rappelle que la décision
SST reste humaine ; le corps de l'écran ne doit pas le contredire.

**R9 — Contraste AA sur tout texte porteur d'état.** Ratio ≥ 4,5:1, ou
≥ 3:1 pour les tailles ≥ 24 px, ou ≥ 18,66 px en gras. Mesuré sur les
paires effectivement utilisées, pas sur la palette déclarée.

**R10 — Clavier et lecteur d'écran complets.** Focus visible sur tout
élément atteignable, ordre de tabulation conforme à l'ordre de lecture,
changement de fiche dans l'inspecteur annoncé par une région `aria-live`,
nom accessible sur tout contrôle.

**R11 — Survit au noir et blanc et à l'impression.** Une capture en
niveaux de gris conserve les quatre états distinguables. C'est le test
terrain : rapport imprimé, projecteur fatigué, écran en plein soleil.

**R12 — L'export porte la provenance de l'écran.** JSON et TTL exportent
`exportedAt`, la source, et la mention qu'aucune décision de conformité
n'est impliquée. Toute nouvelle donnée affichée à l'écran est exportable
avec sa provenance, ou n'est pas affichée.

**R13 — Parité linguistique stricte.** Toute clé `data-i18n` existe dans
`fr` et dans `en`. Une clé manquante dégrade silencieusement en vide, et
un état vide se lit comme un état neutre — c'est une violation de R2 par
un autre chemin.

**R14 — Le code produit est valide, pas seulement présent.** Un commentaire
CSS n'en contient jamais un autre; les accolades s'équilibrent. Un commentaire
imbriqué se referme au premier `*/` et le navigateur ignore silencieusement
tout ce qui suit — sans erreur, sans avertissement. Une règle écrite mais
jamais appliquée satisfait un contrôle de présence tout en ne produisant rien.
C'est le mode de défaillance le plus dangereux d'une vérification mécanique :
elle rassure sans garantir. R1 est resté au vert pendant plusieurs itérations
alors qu'aucun glyphe n'était rendu.

---

## 4. Anti-patrons nommés

À refuser explicitement, même sur demande.

- Feux tricolores vert/orange/rouge sans second canal.
- Jauge de conformité en pourcentage global. Un pourcentage agrège des
  régimes qui ne se fusionnent pas ; c'est la fusion interdite par le
  modèle, déguisée en indicateur.
- Graphe de nœuds et de liens comme vue principale. Le lien y redevient un
  trait, ce que le modèle refuse. Un graphe est acceptable en vue
  secondaire si chaque arête est cliquable vers sa fiche.
- Animation de chargement suggérant un calcul. Rien n'est calculé.
- Dégradés, glassmorphisme, cartes empilées décoratives. `VARIANCE` = 2.
- Score de risque agrégé. Non modélisé, donc non affichable.

---

## 5. Où cette doctrine s'applique

`ax5-explorer/index.html` est aujourd'hui déposé dans le dépôt par copie
depuis un fichier produit ailleurs. Tant que c'est le cas, la doctrine
n'est pas appliquée : elle est écrasée à la régénération suivante. Deux
sorties possibles, dans l'ordre de préférence.

1. La génération de l'explorateur entre dans `generator/`, lit ce fichier,
   et le test tourne en CI comme `validate.py`.
2. À défaut, le test tourne quand même sur le fichier déposé et bloque la
   fusion. La doctrine devient un contrat de recette plutôt qu'un contrat
   de génération. C'est moins bon, mais ce n'est pas rien.

Le test associé est `tests/test_rendu_explorateur.py`. Il ne juge pas le
goût. Il vérifie les treize règles ci-dessus, et il échoue en nommant la
règle violée.
