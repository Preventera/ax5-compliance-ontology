# CLAUDE.md — ax5-compliance-ontology (OntoX5)

Contexte projet pour toute session de travail sur ce dépôt.
Dernière vérification : 1er septembre 2026.

---

## Ce qu'est ce projet

Une **ontologie de conformité multi-juridictionnelle**, plus un générateur qui
transforme une spécification métier en YAML en ontologie OWL, contraintes SHACL
et rapport de décisions.

Le problème traité : plusieurs autorités réglementaires emploient le même terme
avec des définitions et des seuils différents. Un humain devine d'après le
contexte; un agent d'IA calcule et se trompe avec assurance. Le modèle empêche
cette confusion.

Dépôt public, licence MIT, CI verte.
Explorateur en ligne : `preventera.github.io/ax5-compliance-ontology/ax5-explorer/`

**Ce n'est pas un éditeur d'ontologie.** Protégé fait ça, gratuitement et mieux.
Le différenciateur est la génération depuis une spécification métier et la
traçabilité des décisions de modélisation.

---

## Les six décisions de modélisation

Elles sont le cœur du projet. Toute modification doit les respecter ou les
remettre en question explicitement.

**1. On ne fusionne jamais.** Deux concepts juridictionnels ne sont jamais
réunis. Chacun garde sa définition, son seuil, son autorité. L'ancre est une
entrée d'index sans autorité propre. Fusionner détruit la spécificité légale,
la seule chose qu'une réponse de conformité doit préserver.

**2. Une relation qui porte ses propres attributs est une entité.**
`ConceptMapping` porte relation SKOS, confiance, base, auteur PROV-O, statut de
revue. Un trait ne s'audite pas. Règle appliquée trois fois dans le dépôt.

**3. `exactMatch` est une permission, pas une description.** Elle autorise un
agent à substituer un concept à l'autre sans avertir. D'où le seuil de 0,95.

**4. La sévérité est une décision d'aiguillage, pas de gravité.** Trois tests
dans `severity_policy.py` : le défaut produit-il une réponse fausse ou
incomplète? De la donnée légitime échouerait-elle? La contrainte serait-elle
contournée? *Une contrainte que les gens contournent est pire qu'aucune
contrainte.*

**5. Le niveau de décision détermine le régime juridique.** Une caméra qui
signale anonymement n'est pas encadrée comme une qui identifie un travailleur.
Même technique, exposition différente.

**6. Une procédure ne satisfait pas une obligation — quelqu'un affirme qu'elle
la satisfait.** `RevendicationCouverture`, réifiée, datée, attribuée. C'est ce
qui rend possible la question : *quelles obligations ne sont couvertes par rien.*

---

## Arborescence

| Chemin | Contenu |
|---|---|
| `ontology/ax5-compliance.ttl` | Ontologie de base — 100 triplets |
| `data/instances.ttl` | Instances de démonstration — 192 triplets, 5 défauts délibérés |
| `shapes/ax5-shapes.ttl` | Contraintes SHACL |
| `queries/competency.py` | CQ-1 à CQ-8, toutes SELECT |
| `queries/forms.py` | CQ-9 ASK, CQ-10 CONSTRUCT, CQ-11 DESCRIBE |
| `generator/generate.py` | Spec YAML → OWL + SHACL + rapport de décisions |
| `generator/severity_policy.py` | Les trois tests d'aiguillage de sévérité |
| `generator/specs/*.yml` | `sst-quebec`, `supply-chain`, `ia-sst` |
| `generator/queries_couverture.py` | CQ-49 à CQ-54, vocabulaire `sst:` |
| `generated/`, `generated-scm/`, `generated-iasst/` | Sorties du générateur |
| `ax5-explorer/index.html` | Explorateur — fichier unique, ~242 Ko |
| `tools/portability_audit.py` | Audit de portabilité, 5 contrôles |
| `server/app.py` | Serveur FastAPI — plateforme souveraine, MVP |
| `tests/` | 47 tests pytest |
| `validate.py` | Validation SHACL du modèle de base |

---

## Commandes

```bash
# Les 47 tests
cd generator && python -m pytest tests/ -q

# Valider le modèle de base (attendu : 6 violations, 1 avertissement)
python validate.py

# Générer un domaine
python generator/generate.py generator/specs/sst-quebec.yml --out generated/

# Les questions de compétence
python queries/competency.py     # CQ-1..8, SELECT
python queries/forms.py          # CQ-9..11, ASK / CONSTRUCT / DESCRIBE

# Audit de portabilité (attendu : verdict PORTABLE)
python tools/portability_audit.py

# Serveur
pip install -r server/requirements.txt
python server/app.py             # http://127.0.0.1:8000/docs
```

---

## Chiffres vérifiés

À citer tels quels; ne pas les réinventer.

| Mesure | Valeur | Source |
|---|---|---|
| Triplets | 292 (100 + 192) | rdflib |
| Tests | 47 | pytest |
| Verdict SHACL | 6 violations, 1 avertissement | `validate.py` **et** pyshacl |
| Classes / propriétés | 14 classes, 12 objet, 10 données, 42 individus | Protégé 5.6.9 |
| Axiomes de classe | 3 `SubClassOf`, 0 équivalence, 0 disjonction, 0 GCI | Protégé |
| Questions de compétence | 8 + 3 + 6 = 17 | trois fichiers |
| Domaines générés | sst 9 classes / 33 barrières · scm 5 / 20 · iasst 8 / 27 | `generate.py` |
| Barrières dégradées | sst 1 · scm 1 · iasst 3 | rapport de décisions |

**Le modèle est purement déclaratif.** Aucune construction n'exige un
raisonneur. Ce n'est pas une lacune : on ne veut pas qu'une machine infère
qu'un concept québécois s'applique ailleurs. La non-fusion est un refus
d'inférer.

---

## Pièges connus

**Deux vocabulaires cohabitent.** Le modèle de base utilise `ax5:`
(anglais : `ConceptMapping`, `mapsFrom`, `reviewStatus`). Les domaines générés
utilisent `sst:`, `scm:`, `iasst:` (français : `RevendicationCouverture`,
`couvreObligation`, `parDocument`). Ne pas mélanger. Une requête écrite pour
l'un ne tourne pas sur l'autre.

**La validation SHACL peut être vide.** Charger les formes `sst-shapes.ttl`
contre `data/instances.ttl` retourne « conforme » avec zéro violation — parce
que zéro nœud est ciblé, les vocabulaires ne correspondant pas. `server/app.py`
signale ce cas avec `vacuous: true`. Toute nouvelle validation doit compter les
nœuds ciblés avant de conclure.

**`RevendicationCouverture` n'existe que dans les domaines générés**, pas dans
`ontology/ax5-compliance.ttl`. La documentation anglaise l'a traduit en
`CoverageClaim`, qui n'est le nom d'aucune classe réelle. À corriger ou à
assumer explicitement.

**Le moteur SPARQL de l'explorateur est un sous-ensemble.** Écrit en JavaScript,
il gère les quatre formes, les motifs de base, `OPTIONAL`, les `FILTER` simples,
`DISTINCT` et `LIMIT`. Pas d'`UNION`, d'agrégats, de chemins de propriété ni de
`NOT EXISTS`. Il exécute correctement 4 des 11 requêtes stockées; pour les
autres, l'interface affiche le résultat rdflib en le disant. **Ne jamais laisser
ce moteur répondre quand il pourrait se tromper en silence.**

**La table CQ → cas d'usage est un jugement, pas une dérivation.** Elle est
codée en dur dans le script d'intégration de l'explorateur. À revoir.

**Les statuts des 100 cas sont approximatifs.** Sur 33 marqués « démontré »,
seuls 12 sont adossés à une requête exécutable. À l'inverse, une dizaine de cas
« structurel » ou « extrapolé » le sont. L'écart est visible via le filtre
« Avec requête » mais n'a pas été arbitré.

---

## Conventions

**Statuts honnêtes.** Quatre valeurs : *démontré* (exercé par les tests),
*structurel* (la structure le permet, rien ne l'exerce), *extrapolé* (usage
plausible, jamais construit), *absent* (le modèle ne sait pas faire). Ne jamais
promouvoir un statut sans preuve. C'est la signature du projet : *un modèle de
conformité qui ne sait pas dire ce qu'il ignore n'est pas un modèle de
conformité.*

**Le vocabulaire des domaines générés est en français**, celui du modèle de base
en anglais. Ne pas uniformiser sans décision explicite.

**Défauts délibérés.** `data/instances.ttl` contient cinq défauts volontaires
qui produisent les 6 violations. Ne pas les « corriger ».

**Ne pas diffuser les liens Netlify.** Ce sont des pages de génération de
prospects, pas des artefacts techniques. Le dépôt GitHub et l'explorateur
GitHub Pages, oui.

---

## Travailler sur l'explorateur

`ax5-explorer/index.html` est un **fichier unique** : CSS dans un `<style>`,
données et logique dans un `<script>`, i18n dans un objet `T = { fr:{}, en:{} }`.

**Mécanisme bilingue.** Les éléments portent `data-i18n="clé"`. `setLang()`
parcourt tous les `[data-i18n]` et écrit `innerHTML = t(clé)` **sans vérifier
que la clé existe** — une clé manquante affiche `undefined` à l'écran. Toute
nouvelle clé doit être ajoutée dans les deux blocs.

**Point d'accroche du rendu.** `setLang()` appelle `render()`, puis les
fonctions de section. Une nouvelle section s'y branche.

**Modification par patch, pas à la main.** Le fichier fait 242 Ko. Les
intégrations passent par des scripts Python qui insèrent CSS, section, clés
i18n et logique à des points d'ancrage précis, à partir d'une base propre.

**Collisions de noms.** Le script existant déclare `esc`, `q`, `cname`,
`rname`, `dname`, `render`, `pick`, `badge`. Vérifier avant d'ajouter un
identifiant global.

**Tests.** L'explorateur se teste avec jsdom en Node :

```bash
npm install jsdom
node -e "const {JSDOM}=require('jsdom'); /* runScripts:'dangerously' */"
```

Vérifier systématiquement : aucune erreur JS, aucune clé i18n rendant
`undefined`, sections d'origine intactes, bascule FR/EN fonctionnelle.
**wkhtmltopdf n'est pas un test valable** — son moteur est trop ancien pour
exécuter le JavaScript moderne.

---

## Sections de l'explorateur

`s-open` · `s-concepts` · `s-maps` · `s-reqs` · `s-cov` · `s-domains` ·
`s-graph` · `s-sparql` · `s-cases` · `s-lex`

Les trois dernières ajoutées récemment : comparaison des trois domaines
générés, graphe par forces sur 32 nœuds et 37 arcs, console SPARQL.
`s-cases` contient les 100 cas d'usage avec filtres par statut, famille,
recherche, et « Avec requête ».

---

## Le serveur

`server/app.py` — FastAPI, magasin en mémoire, aucun appel sortant.

| Endpoint | Rôle |
|---|---|
| `POST /domains` | Spec YAML → ontologie + formes + décisions |
| `POST /domains/{id}/data` | Charger des instances |
| `POST /domains/{id}/query` | SPARQL, les quatre formes |
| `GET /domains/{id}/validate` | Verdict SHACL, avec détection de validation vide |
| `POST /domains/{id}/guard` | **La barrière** — un agent peut-il substituer? |
| `GET /domains/{id}/{ontology,shapes,decisions}` | Artefacts générés |

`/guard` est la pièce maîtresse : politique paramétrable (seuil de confiance,
exigence de revue humaine), et trois motifs de refus distincts —
`relation_not_exact_match`, `confidence_below_threshold`, `not_human_reviewed`,
plus `no_mapping`. **L'absence de correspondance n'est pas une équivalence.**

Manquant pour un usage réel : authentification, multi-tenant, persistance,
tests.

---

## L'angle qui manque

La grille des sept angles qu'un vocabulaire partagé doit supporter :

| Angle | Question | État |
|---|---|---|
| Portée | Qui a autorité ici? | Acquis |
| Temps | Quand, et selon qui? | Acquis |
| Provenance | Comment le savons-nous? | Acquis |
| Identité | Est-ce la même chose? | Partiel — concepts oui, instances non |
| Composition | De quoi est-ce fait? | Absent |
| Inférence | Qu'est-ce qui en découle? | Absent — choix assumé |
| Désaccord | Deux sources opposées? | **Absent — prochain à construire** |

Le désaccord suit la même récursion que les deux constructions précédentes :
un mapping n'est pas un fait mais une revendication, plusieurs coexistent sur
la même paire, une couche de résolution tranche, datée et attribuée.

---

## Les deux échecs de portage

Le meilleur matériel du projet. Ne pas les effacer.

**Chaîne d'approvisionnement, 2e domaine.** Vingt barrières dures, un seul
avertissement. Les heuristiques de sévérité étaient peuplées du seul vocabulaire
SST. Le ratio était le signal. Limite honnête : *les heuristiques par nom de
champ ne se portent pas seules.*

**IA-SST, 3e domaine.** Deux bogues présents depuis le premier jour, qu'aucun
banc d'essai antérieur n'exerçait. Le générateur ne savait pas exprimer une
condition d'**absence** — il produisait l'inverse de la règle voulue. Et la
sévérité s'appliquait au bloc entier : *« peut être absent » et « peut valoir
n'importe quoi » sont deux affirmations différentes.*

---

## Validations indépendantes

Le modèle a été vérifié par quatre moteurs distincts, qui concordent :

- **rdflib** — parsing, 17 requêtes, sérialisation croisée en 5 formats
- **pyshacl** — 6 violations, 1 avertissement, mêmes chiffres que `validate.py`
- **Protégé 5.6.9 + OWL API** — charge, affiche, ne trouve rien à inférer
- **moteur JavaScript maison** — accord avec rdflib sur 10 requêtes

C'est la preuve de portabilité : le modèle ne dépend pas de l'outillage qui
l'a produit.
