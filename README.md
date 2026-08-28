[![Validate ontology](https://github.com/Preventera/ax5-compliance-ontology/actions/workflows/validate.yml/badge.svg)](https://github.com/Preventera/ax5-compliance-ontology/actions/workflows/validate.yml)
# AX5 Compliance Ontology — projet d'apprentissage

**Objectif double.** Apprendre RDF, SHACL et SPARQL par la pratique, sur un domaine que tu connais déjà — et produire du même coup l'artéfact que tu défendras devant le panel Kinaxis.

Tout est exécutable. Rien n'est théorique.

---

## Démarrage

```bash
pip install rdflib pyshacl
cd ax5-onto

python3 validate.py               # validation SHACL — trouve 6 violations + 1 warning
python3 queries/competency.py     # les 8 questions de compétence en SPARQL
```

## Structure

```
ontology/ax5-compliance.ttl   Le modèle : classes, propriétés, commentaires de conception
data/instances.ttl            Les faits — contient 5 ERREURS DÉLIBÉRÉES
shapes/ax5-shapes.ttl         Les contrats SHACL, dont 3 en SHACL-SPARQL
queries/competency.py         Les 8 questions de compétence
validate.py                   Le validateur
```

---

## La décision de modélisation centrale

**On ne fusionne jamais un concept juridictionnel dans un concept canonique unique.**

L'instinct naturel est de créer un « Recordable Injury » canonique et d'y rabattre CNESST, OSHA, HSE UK. C'est faux, et savoir pourquoi c'est faux est exactement ce qui distingue un ontologiste d'un intégrateur : la fusion détruit la spécificité légale, c'est-à-dire la seule chose qu'une réponse de conformité doit préserver. Un agent qui répond à partir du concept fusionné produit une réponse fluide et fausse dans l'une des deux juridictions.

Le modèle retenu a donc trois niveaux :

- **`AnchorConcept`** — pivot neutre, sans force légale. Sert uniquement à traverser d'un régime à l'autre.
- **`JurisdictionalConcept`** — le concept tel que défini dans *un* régime. Garde son seuil, son unité, son libellé d'origine.
- **`ConceptMapping`** — ⚠️ **une entité, pas un triplet.**

### Pourquoi le mapping est une entité

`skos:closeMatch` est un simple triplet. Il ne peut porter ni confiance, ni auteur, ni base, ni date, ni statut de revue. Or ce sont précisément les attributs dont une assertion inter-juridictionnelle a besoin pour être auditable.

> **Dès qu'une relation porte ses propres attributs et son propre cycle de vie, c'est une entité.**

C'est la même règle qui fait qu'un `BOMEdge` doit être un objet de première classe dans un modèle supply chain — il porte des dates d'effectivité, un rendement, des alternatives. Et c'est le pont que tu traces en entrevue.

---

## Parcours d'apprentissage — environ 8 heures

### Bloc 1 · Lire le modèle (1 h)
Ouvre `ontology/ax5-compliance.ttl`. Les commentaires expliquent chaque décision. Repère les trois niveaux de concepts et le bloc bitemporel.

**Fais-le :** ajoute une classe `Worker` avec une propriété `holdsCertification` vers une nouvelle classe `Certification`. Recharge, vérifie que rien ne casse.

### Bloc 2 · Casser et réparer (2 h)
Lance `validate.py`. Six violations, un warning. Les cinq erreurs sont commentées dans `data/instances.ttl` — **ne les lis qu'après** avoir tenté de les identifier depuis le rapport.

**Fais-le :** répare-les une à une, en relançant à chaque fois. Puis introduis une erreur *nouvelle* de ton cru et vérifie que SHACL l'attrape. Si elle passe, ta shape est trop permissive — c'est l'exercice.

### Bloc 3 · Le choix Violation vs Warning (30 min)
Regarde `RequirementShape`. La citation est bloquante; le rattachement à un danger ne l'est pas.

**Réfléchis :** pourquoi? La réponse est dans le commentaire, mais formule-la toi-même avant de lire. C'est une décision d'architecte, pas de modélisateur, et un panel peut te la poser.

### Bloc 4 · SHACL-SPARQL (1 h 30)
Les shapes 4, 5 et 6 font ce que les composants standards ne peuvent pas : croiser deux propriétés d'un même nœud, ou traverser deux arcs.

**Fais-le :** écris une septième shape. Suggestion — *un mapping `human-reviewed` doit être attribué à un `prov:Person`, pas à un `prov:SoftwareAgent`*. C'est une règle de gouvernance réelle et elle exige du SPARQL.

### Bloc 5 · Les requêtes (2 h)
Lance `queries/competency.py`. Étudie surtout **CQ-2** (chemins de propriété) et **CQ-4** (`NOT EXISTS`).

**Fais-le :** écris trois nouvelles questions de compétence. Suggestions :
- Quelles exigences s'appliquent à la même tâche sur le site de Toledo plutôt que Bromont? *(même requête, juridiction différente — c'est tout l'intérêt du modèle)*
- Quels mappings ont une confiance sous 0.6 tout en étant `human-reviewed`? *(désaccord entre confiance et statut)*
- Quelles exigences sont en vigueur aujourd'hui mais ont été enregistrées après une date donnée? *(les deux axes temporels ensemble)*

### Bloc 6 · Faire le pont (1 h)
Réécris le même modèle pour la supply chain. `AnchorConcept` devient un concept canonique (« site », « lead time »), `JurisdictionalConcept` devient un concept propre à un système source (SAP, WMS, Salesforce), `ConceptMapping` reste exactement ce qu'il est.

**C'est le bloc le plus important pour l'entrevue.** Il te permet de dire : *« j'ai résolu cette forme de problème, voici le modèle, et voici sa transposition chez vous. »*

---

## Les cinq erreurs (ne pas lire avant le bloc 2)

<details>
<summary>Déplier</summary>

1. `CPT-ORPHAN-Something` — concept juridictionnel sans juridiction.
2. `MAP-004` — `exactMatch` déclaré avec une confiance de 0.55, sous le seuil de politique de 0.95.
3. `MAP-005` — mapping intra-juridictionnel (QC → QC), ce qui contredit la définition.
4. `MAP-006` — mapping sans base ni auteur : non auditable. *(compte pour deux violations)*
5. `REQ-UK-CS-RiskAssess` — exigence sans citation.

Et un warning voulu : `REQ-INT-45001-Consult` sans danger rattaché.

</details>

---

## Ce que ce projet te permet de dire en entrevue

**Sur SHACL vs OWL :**
> "OWL runs under the open-world assumption, so a cardinality axiom doesn't reject anything — it makes the reasoner infer that two values denote the same thing. OWL infers what else must be true; SHACL checks what must be present. I've got working shapes for both the simple constraints and the ones that need SHACL-SPARQL because they cross two properties on the same node."

**Sur le multi-juridictionnel :**
> "The instinct is to merge everything into one canonical concept. That destroys the legal specificity, which is the one thing a compliance answer needs. So jurisdiction-scoped concepts stay first-class, and the mapping between them is a reified entity carrying relation type, confidence, basis, asserter and review status. Exact matches turned out to be rare — most of the real work is in the near-misses, and the model has to be able to say that no mapping exists."

**Sur les évaluateurs — la connexion que peu de gens font :**
> "The competency questions I used to scope the ontology are the same set I use to evaluate the agents. Scoping artifact and eval harness are the same object. And the most valuable query isn't the one that finds matches — it's the one that finds the holes, so the agent can say 'no equivalent exists in that regime' instead of inventing a plausible one."

**Sur le pont vers la supply chain :**
> "'Site', 'capacity' and 'lead time' don't mean the same thing in SAP, a WMS, Salesforce and Maestro either. Same structure, same temptation to force one merged definition, and I think it's the same mistake."

---

## Limites — à dire, pas à cacher

- Quatre juridictions, une poignée de concepts. C'est un modèle jouet.
- Aucun raisonnement OWL n'est activé : `inference="none"` dans `validate.py`. Volontaire, et défendable — voir la position sur matérialisation vs réécriture.
- Pas de gestion multi-tenant, pas de contrôle d'accès.
- Le versionnage est déclaré (`owl:versionInfo`) mais pas outillé.

Nommer ces limites toi-même vaut mieux que de les faire découvrir.
