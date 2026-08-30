# Rapport de génération — Sémantique multi-systèmes — chaîne d'approvisionnement

Ce rapport explique **pourquoi** chaque contrainte a la sévérité
qu'elle a. Il se lit sans connaître SHACL.

Rappel des trois tests :

1. Le défaut produit-il une réponse **fausse** ou seulement **incomplète** ?
2. De la donnée **légitime** peut-elle échouer à la contrainte ?
3. La contrainte serait-elle **contournée** par l'équipe d'ingestion ?

## ⚠ Champs dégradés par le générateur

Ces champs sont déclarés obligatoires dans le spec, mais la
politique de sévérité refuse d'en faire une barrière dure.

### `RegleDePlanif.appliesToConcept`

- Déclaré : **obligatoire**
- Généré : **Warning**
- Test appliqué : TEST 2 : de la donnée légitime échouerait
- Raison : De la donnée légitime peut ne pas avoir de 'appliesToConcept'. Bloquer rejetterait du vrai. On tolère et on suit le trou comme métrique de couverture.

## Toutes les décisions

| Fiche | Champ | Sévérité | Test |
|---|---|---|---|
| SystemeSource | `nom` | Violation | Aucun test échoué : blocage sûr |
| SystemeSource | `code` | Violation | Aucun test échoué : blocage sûr |
| ConceptSysteme | `libelle` | Violation | Aucun test échoué : blocage sûr |
| ConceptSysteme | `scopedTo` | Violation | TEST 1 : produit une réponse fausse |
| ConceptSysteme | `definition` | Violation | Aucun test échoué : blocage sûr |
| AncrageMetier | `libelle` | Violation | Aucun test échoué : blocage sûr |
| AncrageMetier | `definition` | Violation | Aucun test échoué : blocage sûr |
| Rapprochement | `source` | Violation | Aucun test échoué : blocage sûr |
| Rapprochement | `cible` | Violation | Aucun test échoué : blocage sûr |
| Rapprochement | `ancrage` | Violation | Aucun test échoué : blocage sûr |
| Rapprochement | `mappingRelation` | Violation | Aucun test échoué : blocage sûr |
| Rapprochement | `confidence` | Violation | TEST 1 : produit une réponse fausse |
| Rapprochement | `basis` | Violation | TEST 1 : produit une réponse fausse |
| Rapprochement | `wasAttributedTo` | Violation | TEST 1 : produit une réponse fausse |
| Rapprochement | `recordedAt` | Violation | TEST 1 : produit une réponse fausse |
| RegleDePlanif | `enonce` | Violation | Aucun test échoué : blocage sûr |
| RegleDePlanif | `citation` | Violation | TEST 1 : produit une réponse fausse |
| RegleDePlanif | `statedIn` | Violation | TEST 1 : produit une réponse fausse |
| RegleDePlanif | `validFrom` | Violation | TEST 1 : produit une réponse fausse |
| RegleDePlanif | `recordedAt` | Violation | TEST 1 : produit une réponse fausse |
| RegleDePlanif | `appliesToConcept` | Warning | TEST 2 : de la donnée légitime échouerait |

## Résumé

- 20 barrières dures (Violation)
- 1 signaux doux (Warning)
- 3 règles métier en SHACL-SPARQL

Un ratio proche de 100 % de barrières dures est un signal d'alarme :
il annonce un pipeline que l'équipe d'ingestion va contourner.
