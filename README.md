# AX5 Compliance Ontology

**Ontologie et contrats de données SHACL pour le raisonnement de conformité SST multi-juridictionnel, avec un générateur piloté par spécification.**

[![Validate ontology](https://github.com/Preventera/ax5-compliance-ontology/actions/workflows/validate.yml/badge.svg)](https://github.com/Preventera/ax5-compliance-ontology/actions/workflows/validate.yml)

### ▸ [Explorateur en ligne — FR / EN](https://preventera.github.io/ax5-compliance-ontology/ax5-explorer/)

Vue en lecture seule : les définitions juridictionnelles côte à côte, les
correspondances avec leur confiance et leur provenance, et les violations
signalées avec leur justification. Aucune installation.

---

## Le problème

« Espace clos » ne désigne pas la même chose au Québec, chez OSHA et au
Royaume-Uni. « Lésion enregistrable » non plus : le Québec compte un jour
d'absence du travail, OSHA compte un soin médical au-delà des premiers soins.
Deux seuils incompatibles sous le même mot.

Un agent qui répond à une question de conformité doit savoir de quel régime il
parle. S'il ne le sait pas, il produit une réponse fluide et fausse — la pire
espèce, parce qu'elle a l'air correcte.

## La décision de modélisation centrale

**On ne fusionne jamais un concept juridictionnel dans un concept canonique
unique.**

L'instinct est de créer un « Recordable Injury » canonique et d'y rabattre
CNESST, OSHA et HSE. La fusion détruit la spécificité légale — précisément la
seule chose qu'une réponse de conformité doit préserver.

Le modèle a donc trois niveaux :

- **`AnchorConcept`** — pivot neutre, sans force légale. Sert uniquement à
  traverser d'un régime à l'autre. Ce n'est jamais une réponse, c'est une
  entrée d'index.
- **`JurisdictionalConcept`** — le concept tel que défini dans *un* régime.
  Garde son seuil, son unité, son libellé d'origine.
- **`ConceptMapping`** — **une entité, pas un triplet.**

### Pourquoi la correspondance est une entité

`skos:closeMatch` est un simple triplet. Il ne peut porter ni confiance, ni
auteur, ni base, ni date, ni statut de revue. Or ce sont exactement les
attributs dont une assertion inter-juridictionnelle a besoin pour être
auditable. Quand un chiffre de conformité est contesté, c'est cette fiche qu'on
ouvre.

> **Dès qu'une relation porte ses propres attributs et son propre cycle de vie,
> c'est une entité.**

C'est la même règle qui fait qu'un `BOMEdge` doit être un objet de première
classe dans un modèle de chaîne d'approvisionnement : il porte des dates
d'effectivité, un rendement, des alternatives.

### La politique sur `exactMatch`

`exactMatch` autorise un agent à substituer un concept à l'autre **sans avertir
l'utilisateur**. Une contrainte SHACL-SPARQL exige donc une confiance d'au
moins 0,95 pour ce type de relation. En dessous, la déclaration doit être
dégradée en `closeMatch`, ce qui oblige l'agent à signaler l'approximation.

Dans les données d'exemple, `MAP-004` déclare `exactMatch` à 0,55 entre la
lésion déclarable québécoise et le cas enregistrable OSHA. La contrainte le
bloque.

---

## Contenu du dépôt

| Dossier | Ce que c'est |
|---|---|
| `ontology/` | Le modèle : classes, propriétés, commentaires de conception |
| `data/` | Les faits — contient **5 erreurs délibérées** |
| `shapes/` | Les contrats SHACL, dont 3 en SHACL-SPARQL |
| `queries/` | 8 questions de compétence en SPARQL |
| `tests/` | 10 tests vérifiant que les shapes attrapent les défauts connus |
| `generator/` | Générateur : spec en langage métier → ontologie + shapes |
| `ax5-explorer/` | Explorateur bilingue en lecture seule |

## Démarrage

```bash
pip install -r requirements.txt

python validate.py               # 6 violations, 1 avertissement
python queries/competency.py     # les 8 questions de compétence
python -m pytest tests/ -q       # 10 tests
```

---

## Le générateur

`generator/` produit l'ontologie OWL, les shapes SHACL et un rapport de
décisions à partir d'un spec YAML écrit en langage métier. Aucun RDF à écrire.

```bash
cd generator
python generate.py specs/sst-quebec.yml --out ../generated
python -m pytest tests/ -q       # 28 tests, deux domaines
```

### La politique de sévérité

Le cœur du générateur est `severity_policy.py`. Trois tests décident entre
bloquer et avertir :

1. Le défaut produit-il une réponse **fausse** ou seulement **incomplète** ?
2. De la donnée **légitime** peut-elle échouer à la contrainte ?
3. La contrainte serait-elle **contournée** par l'équipe d'ingestion ?

Le générateur **contredit le spec** quand il le faut, et écrit pourquoi.
`addressesHazard` y est déclaré obligatoire; le générateur le dégrade en
avertissement, parce qu'ISO 45001 §5.4 — la consultation des travailleurs — est
une exigence de système de gestion qui ne vise légitimement aucun danger unique.
Bloquer rejetterait de la donnée valide, ou pousserait quelqu'un à inventer un
rattachement bidon.

> **Une contrainte que les gens contournent est pire qu'aucune contrainte.**
> Barrière dure là où la mauvaise donnée produit une réponse fausse et assurée.
> Signal doux là où la donnée est incomplète mais honnête.

### Portabilité

`generator/specs/supply-chain.yml` génère un domaine de sémantique
multi-systèmes pour la chaîne d'approvisionnement — **sans qu'une ligne de code
change**. `SystemeSource` remplace `Juridiction`, `Rapprochement` remplace
`ConceptMapping`, et la décision de modélisation est identique : on ne fusionne
pas le `PLIFZ` de SAP (jours calendrier, transit exclu) avec le `LEAD_DAYS` du
WMS (jours ouvrables, transit inclus).

**Ce que le portage a révélé.** Première génération : 21 barrières dures, zéro
avertissement. Les heuristiques de sévérité étaient peuplées du seul vocabulaire
SST, donc `appliesToConcept` — pourtant l'exact équivalent de `addressesHazard`
— est sorti en barrière dure. Le ratio était le signal : un domaine sans aucun
signal doux annonce un pipeline que l'équipe d'ingestion va contourner.

C'est la limite honnête de l'approche : **les heuristiques par nom de champ ne se
portent pas seules**. Un générateur mûr déclarerait ces catégories dans le spec
plutôt que dans le code. `test_au_moins_un_signal_doux` verrouille la régression
pour le prochain domaine.

Détail complet dans [`generator/README.md`](generator/README.md).

---

## Bitemporalité

Deux axes, pas un :

- `validFrom` / `validTo` — quand la règle est en vigueur
- `recordedAt` / `retractedAt` — quand nous l'avons su

Après un accident, l'enquêteur ne demande pas seulement quelle était la règle.
Il demande **ce que l'employeur savait à ce moment-là**. Un modèle mono-temporel
ne peut pas répondre.

---

## Les cinq erreurs délibérées

Les données d'exemple contiennent cinq défauts. Le validateur doit tous les
trouver — c'est ce que les tests vérifient.

<details>
<summary>Déplier</summary>

1. `CPT-ORPHAN-Something` — concept juridictionnel sans juridiction.
2. `MAP-004` — `exactMatch` à 0,55, sous le seuil de politique de 0,95.
3. `MAP-005` — correspondance intra-juridictionnelle (QC → QC), ce qui
   contredit la définition d'une correspondance.
4. `MAP-006` — sans base ni auteur : non auditable. *(deux violations)*
5. `REQ-UK-CS-RiskAssess` — exigence sans citation.

Plus un avertissement voulu : `REQ-INT-45001-Consult` sans danger rattaché.

</details>

Les tests ne vérifient pas que le graphe est propre. Ils vérifient que les
**contraintes attrapent les défauts connus** et laissent passer la donnée
valide. Un contrat trop permissif est pire qu'inutile : il donne une fausse
assurance de qualité.

---

## Limites

Nommées plutôt que cachées.

- Quatre juridictions, une poignée de concepts. C'est un modèle de
  démonstration, pas un référentiel réglementaire.
- Aucun raisonnement OWL n'est activé (`inference="none"`). Choix délibéré :
  la validation porte sur ce qui est présent, pas sur ce qui est inférable.
- Pas de gestion multi-tenant, pas de contrôle d'accès.
- Le versionnage est déclaré (`owl:versionInfo`) mais pas outillé.
- `citation` est une chaîne de caractères, pas une référence résoluble vers le
  texte source. Le lignage vers le document physique manque.
- La boucle de vérification s'arrête au RDF généré, jamais à l'intention du
  praticien qui a écrit le spec.

**Ce système ne rend pas de décision de conformité.** Il cite, il attribue, il
signale son niveau de confiance, et il route vers un humain. La décision SST
reste humaine.

---

## Licence

Code sous licence MIT. © 2026 AgenticX5 · Mario Deshaies.
