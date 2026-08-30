# Rapport de génération — Applications de l'IA en santé et sécurité du travail

Ce rapport explique **pourquoi** chaque contrainte a la sévérité
qu'elle a. Il se lit sans connaître SHACL.

Rappel des trois tests :

1. Le défaut produit-il une réponse **fausse** ou seulement **incomplète** ?
2. De la donnée **légitime** peut-elle échouer à la contrainte ?
3. La contrainte serait-elle **contournée** par l'équipe d'ingestion ?

## ⚠ Champs dégradés par le générateur

Ces champs sont déclarés obligatoires dans le spec, mais la
politique de sévérité refuse d'en faire une barrière dure.

### `TechniqueIA.lexiconRef`

- Déclaré : **obligatoire**
- Généré : **Warning**
- Test appliqué : TEST 2 : de la donnée légitime échouerait
- Raison : De la donnée légitime peut ne pas avoir de 'lexiconRef'. Bloquer rejetterait du vrai. On tolère et on suit le trou comme métrique de couverture.

### `ApplicationIA.viseGenreAccident`

- Déclaré : **obligatoire**
- Généré : **Warning**
- Test appliqué : TEST 2 : de la donnée légitime échouerait
- Raison : De la donnée légitime peut ne pas avoir de 'viseGenreAccident'. Bloquer rejetterait du vrai. On tolère et on suit le trou comme métrique de couverture.

### `ApplicationIA.appliesToSector`

- Déclaré : **obligatoire**
- Généré : **Warning**
- Test appliqué : TEST 2 : de la donnée légitime échouerait
- Raison : De la donnée légitime peut ne pas avoir de 'appliesToSector'. Bloquer rejetterait du vrai. On tolère et on suit le trou comme métrique de couverture.

## Toutes les décisions

| Fiche | Champ | Sévérité | Test |
|---|---|---|---|
| TechniqueIA | `libelle` | Violation | Aucun test échoué : blocage sûr |
| TechniqueIA | `definition` | Violation | Aucun test échoué : blocage sûr |
| TechniqueIA | `lexiconRef` | Warning | TEST 2 : de la donnée légitime échouerait |
| FamilleDanger | `libelle` | Violation | Aucun test échoué : blocage sûr |
| FamilleDanger | `refNorme` | Violation | Aucun test échoué : blocage sûr |
| GenreAccident | `libelle` | Violation | Aucun test échoué : blocage sûr |
| GenreAccident | `codeCNESST` | Violation | Aucun test échoué : blocage sûr |
| GenreAccident | `scopedTo` | Violation | TEST 1 : produit une réponse fausse |
| SecteurSCIAN | `libelle` | Violation | Aucun test échoué : blocage sûr |
| SecteurSCIAN | `codeSCIAN` | Violation | Aucun test échoué : blocage sûr |
| TypeIntervention | `libelle` | Violation | Aucun test échoué : blocage sûr |
| TypeIntervention | `rangHierarchie` | Warning | TEST 2 : de la donnée légitime échouerait |
| Juridiction | `nom` | Violation | Aucun test échoué : blocage sûr |
| Juridiction | `code` | Violation | Aucun test échoué : blocage sûr |
| EncadrementJuridique | `libelle` | Violation | Aucun test échoué : blocage sûr |
| EncadrementJuridique | `citation` | Violation | TEST 1 : produit une réponse fausse |
| EncadrementJuridique | `scopedTo` | Violation | TEST 1 : produit une réponse fausse |
| EncadrementJuridique | `declencheur` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `libelle` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `emploieTechnique` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `viseDanger` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `viseGenreAccident` | Warning | TEST 2 : de la donnée légitime échouerait |
| ApplicationIA | `appliesToSector` | Warning | TEST 2 : de la donnée légitime échouerait |
| ApplicationIA | `typeIntervention` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `scopedTo` | Violation | TEST 1 : produit une réponse fausse |
| ApplicationIA | `niveauDecision` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `maturite` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `risqueDocumente` | Violation | Aucun test échoué : blocage sûr |
| ApplicationIA | `basis` | Violation | TEST 1 : produit une réponse fausse |
| ApplicationIA | `wasAttributedTo` | Violation | TEST 1 : produit une réponse fausse |
| ApplicationIA | `recordedAt` | Violation | TEST 1 : produit une réponse fausse |

## Résumé

- 27 barrières dures (Violation)
- 4 signaux doux (Warning)
- 2 règles métier en SHACL-SPARQL

Un ratio proche de 100 % de barrières dures est un signal d'alarme :
il annonce un pipeline que l'équipe d'ingestion va contourner.
