# Rapport de génération — Conformité SST Québec

Ce rapport explique **pourquoi** chaque contrainte a la sévérité
qu'elle a. Il se lit sans connaître SHACL.

Rappel des trois tests :

1. Le défaut produit-il une réponse **fausse** ou seulement **incomplète** ?
2. De la donnée **légitime** peut-elle échouer à la contrainte ?
3. La contrainte serait-elle **contournée** par l'équipe d'ingestion ?

## ⚠ Champs dégradés par le générateur

Ces champs sont déclarés obligatoires dans le spec, mais la
politique de sévérité refuse d'en faire une barrière dure.

### `Obligation.addressesHazard`

- Déclaré : **obligatoire**
- Généré : **Warning**
- Test appliqué : TEST 2 : de la donnée légitime échouerait
- Raison : De la donnée légitime peut ne pas avoir de 'addressesHazard'. Bloquer rejetterait du vrai. On tolère et on suit le trou comme métrique de couverture.

## Toutes les décisions

| Fiche | Champ | Sévérité | Test |
|---|---|---|---|
| Obligation | `citation` | Violation | TEST 1 : produit une réponse fausse |
| Obligation | `enonce` | Violation | Aucun test échoué : blocage sûr |
| Obligation | `statedIn` | Violation | TEST 1 : produit une réponse fausse |
| Obligation | `validFrom` | Violation | TEST 1 : produit une réponse fausse |
| Obligation | `recordedAt` | Violation | TEST 1 : produit une réponse fausse |
| Obligation | `addressesHazard` | Warning | TEST 2 : de la donnée légitime échouerait |
| Reglement | `titre` | Violation | Aucun test échoué : blocage sûr |
| Reglement | `hasJurisdiction` | Violation | Aucun test échoué : blocage sûr |
| Juridiction | `nom` | Violation | Aucun test échoué : blocage sûr |
| Juridiction | `code` | Violation | Aucun test échoué : blocage sûr |
| Danger | `libelle` | Violation | Aucun test échoué : blocage sûr |
| ConceptLocal | `libelle` | Violation | Aucun test échoué : blocage sûr |
| ConceptLocal | `scopedTo` | Violation | TEST 1 : produit une réponse fausse |
| Correspondance | `source` | Violation | Aucun test échoué : blocage sûr |
| Correspondance | `cible` | Violation | Aucun test échoué : blocage sûr |
| Correspondance | `mappingRelation` | Violation | Aucun test échoué : blocage sûr |
| Correspondance | `confidence` | Violation | TEST 1 : produit une réponse fausse |
| Correspondance | `basis` | Violation | TEST 1 : produit une réponse fausse |
| Correspondance | `wasAttributedTo` | Violation | TEST 1 : produit une réponse fausse |

## Résumé

- 18 barrières dures (Violation)
- 1 signaux doux (Warning)
- 3 règles métier en SHACL-SPARQL

Un ratio proche de 100 % de barrières dures est un signal d'alarme :
il annonce un pipeline que l'équipe d'ingestion va contourner.
