# Générateur ontologique AX5

Vous décrivez votre domaine en langage métier. Le générateur produit
l'ontologie, les contraintes de qualité, et un rapport expliquant chacun
de ses choix.

Aucune ligne de RDF à écrire.

```bash
python generate.py specs/sst-quebec.yml --out ../generated/
```

---

## 1. Le vocabulaire, traduit

Six mots à connaître. Vous connaissez déjà les six concepts — ce sont
les noms qui sont étrangers.

| Terme technique | Ce que c'est, dans votre réalité |
|---|---|
| **Ontologie** | Le formulaire vierge. Quelles fiches existent, quels champs elles portent, comment elles se relient. |
| **Classe** | Un type de fiche. « Obligation », « Règlement », « Danger ». |
| **Propriété** | Un champ sur la fiche. « Référence de l'article », « En vigueur depuis ». |
| **Instance** | Une fiche remplie. L'article 302 du RSST, pas la notion d'obligation. |
| **SHACL** | La checklist de vérification avant qu'un dossier soit classé. Champs obligatoires, valeurs cohérentes. |
| **SPARQL** | La question posée au dossier. « Donne-moi toutes les obligations en vigueur au Québec le 3 mars 2024. » |

Un détail qui compte : **l'ontologie et les données sont le même
format**. Contrairement à une base relationnelle où le schéma vit à part,
ici la structure est de la donnée. C'est ce qui permet de la faire
évoluer sans migration.

---

## 2. Le modèle de conformité, en langage SST

**`Reglement`** — le document complet. Le RSST, la LSST, 29 CFR 1910,
ISO 45001.

**`Obligation`** — l'article précis dans ce document. Pas « le RSST »,
mais l'obligation nommée, avec sa référence exacte. C'est pourquoi la
citation est obligatoire : un conseiller SST qui affirme une obligation
sans pouvoir pointer l'article se fait démolir en audit. Un agent aussi.

**`ConceptLocal`** — « espace clos » **tel que le Québec le définit**.
Et séparément, « confined space » **tel qu'OSHA le définit**. Deux fiches
distinctes, parce que les définitions et les seuils diffèrent.

> **La décision centrale du modèle : on ne fusionne jamais.**
> Écraser les deux dans un concept unique détruit la spécificité légale
> — précisément ce dont un agent a besoin pour répondre juste.

**`Correspondance`** — la fiche qu'un conseiller SST écrit à la main
quand une entreprise s'implante aux États-Unis. « Au Québec on dit ceci,
chez OSHA on dit cela, c'est proche mais pas identique parce que le
seuil d'oxygène diffère. »

Cette fiche porte quatre choses :

| Champ | Ce qu'il répond |
|---|---|
| `mappingRelation` | À quel point c'est équivalent |
| `confidence` | À quel point vous en êtes sûr |
| `basis` | Sur quelle base vous l'affirmez |
| `wasAttributedTo` | Qui signe |

> **Deuxième décision centrale : la correspondance est une fiche, pas un
> trait.** Un trait entre deux cases ne peut pas être audité. Une fiche
> qui a un auteur, une justification et une date, oui.

**`validFrom` / `validTo`** — quand la règle est en vigueur.
**`recordedAt`** — quand *vous* l'avez inscrite au système.

Deux axes différents, et vous savez pourquoi : après un accident,
l'enquêteur ne demande pas seulement quelle était la règle. Il demande
**ce que l'employeur savait à ce moment-là**. Sans les deux axes, la
question n'a pas de réponse.

---

## 3. Ce que le générateur décide à votre place

C'est la partie qui vaut le détour.

Dans le spec, vous déclarez un champ obligatoire. Le générateur ne suit
pas toujours. Il applique trois tests avant de choisir entre **bloquer**
et **avertir** :

1. Le défaut produit-il une réponse **fausse**, ou seulement
   **incomplète** ?
2. De la donnée **légitime** peut-elle échouer à cette contrainte ?
3. La contrainte serait-elle **contournée** par l'équipe d'ingestion ?

Exemple concret, tiré du spec fourni. `addressesHazard` y est déclaré
obligatoire. Le générateur le dégrade en avertissement et l'écrit :

```
DÉGRADATIONS (le générateur refuse la barrière dure) :
  - Obligation.addressesHazard  ->  sh:Warning
    TEST 2 : de la donnée légitime échouerait
```

Pourquoi : l'article 5.4 d'ISO 45001, la consultation des travailleurs,
ne se rattache légitimement à aucun danger unique. C'est une exigence de
système de gestion, pas une mesure de maîtrise. Rendre le champ
obligatoire produirait deux issues, et les deux sont mauvaises : soit on
rejette de la donnée valide, soit l'équipe d'ingestion invente un lien
bidon pour franchir la barrière. La deuxième est pire — le graphe
contient maintenant une fabrication qui a l'air autorisée.

> **La règle : une contrainte que les gens contournent est pire
> qu'aucune contrainte.**
>
> Barrière dure là où la mauvaise donnée produit une réponse fausse et
> assurée. Signal doux là où la donnée est incomplète mais honnête.

La logique complète est dans [`severity_policy.py`](severity_policy.py),
commentée ligne par ligne. C'est le seul module du générateur qui
contienne un vrai jugement d'architecte — tout le reste est de la
mécanique.

---

## 4. Les règles que les champs obligatoires ne savent pas dire

Certaines règles croisent plusieurs champs, ou traversent plusieurs
fiches. Le SHACL ordinaire contraint **un chemin à la fois** : il ne sait
pas exprimer « si le champ A vaut X alors le champ B doit satisfaire Y ».

Le générateur traduit ces règles en SHACL-SPARQL. Vous les écrivez comme
ça :

```yaml
- nom: seuil_equivalence_exacte
  sur: Correspondance
  type: condition_croisee
  libelle: >
    On ne déclare pas une équivalence exacte entre deux régimes sur une
    preuve faible. C'est ainsi qu'on produit une réponse fluide et fausse.
  si:
    champ: mappingRelation
    vaut: "exactMatch"
  alors:
    champ: confidence
    minimum: 0.95
```

**Le renversement à comprendre :** en SHACL-SPARQL, la requête générée
décrit ce qui est **interdit**, pas ce qui est valide. Toute ligne
retournée est une violation. Zéro ligne retournée signifie conforme.

Conséquence visible dans les rapports : ces contraintes portent sur le
**nœud entier**, pas sur un champ. Le rapport affiche donc `-` dans la
colonne propriété au lieu d'un nom de champ. **La forme du rapport vous
dit quel type de contrainte a tiré.**

Trois formes de règles sont supportées :

| Type | Ce qu'il exprime |
|---|---|
| `condition_croisee` | Si le champ A vaut X, le champ B doit satisfaire Y |
| `comparaison_traversee` | Suivre deux chemins et comparer ce qu'on trouve au bout |
| *(à venir)* | Vos règles — le générateur est fait pour être étendu |

---

## 5. Le banc d'essai

`tests/fixture_defauts.ttl` contient sept défauts plantés
volontairement, plus un cas de référence valide.

```bash
python -m pytest tests/ -q
```

Ce qu'on teste n'est pas que le générateur produit du RDF — n'importe
quel gabarit fait ça. On teste que les shapes produites **attrapent les
défauts connus** et **laissent passer la donnée valide**.

Sortie attendue : **6 violations, 1 avertissement**.

`test_compte_total` verrouille ces nombres. S'il échoue après une
modification du générateur, la question n'est pas « comment le faire
passer » — c'est **« quelle contrainte ai-je affaiblie sans m'en rendre
compte »**.

---

## 6. Étendre le générateur

Pour ajouter un champ ou une fiche : modifiez le spec, relancez. Le
fichier généré porte l'avertissement `Ce fichier est GÉNÉRÉ` — ne le
modifiez pas à la main.

Pour ajouter une heuristique de sévérité : les trois ensembles en bas de
`severity_policy.py`.

```python
FIELDS_PRODUCING_WRONG_ANSWERS = { "citation", "scopedTo", ... }
FIELDS_WITH_LEGITIMATE_GAPS    = { "addressesHazard", "validTo", ... }
FIELDS_LIKELY_GAMED            = { "reviewedBy", "riskScore", ... }
```

Ce sont des **propositions**, pas des verdicts : le spec peut toujours
les écraser. Un générateur qui impose ses choix à l'expert du domaine ne
sera pas utilisé — et un vocabulaire que seuls ses auteurs peuvent lire
ne sera pas maintenu.

---

## 7. Portabilité

Le spec ne contient aucun terme propre à la SST. `fiches`, `champs`,
`regles` — le vocabulaire est générique. Le domaine réglementaire n'est
qu'un exemple.

Écrivez un spec où `ConceptLocal` devient « site tel que SAP le
définit », `Correspondance` devient la fiche de rapprochement entre deux
systèmes, et vous obtenez la même chose pour la chaîne
d'approvisionnement. La décision de modélisation est identique : on ne
fusionne pas « lead time » de SAP avec « lead time » du WMS, on modélise
le rapport entre les deux, et ce rapport a un auteur.
