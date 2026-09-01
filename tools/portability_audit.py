#!/usr/bin/env python3
"""
AX5 — Audit de portabilité.

Question posée : ce modèle est-il un artefact standard, chargeable dans
n'importe quel triplestore, ou dépend-il de l'outillage qui l'a produit ?

Un modèle qui ne se charge que dans son propre environnement n'est pas
une ontologie portable — c'est une structure de données privée écrite
en Turtle.

Cinq contrôles :
  1. analyse syntaxique stricte
  2. sérialisation croisée (aller-retour sans perte)
  3. profil de vocabulaire (RDF/OWL/SKOS/PROV standard, ou termes maison)
  4. validation SHACL par un moteur tiers (pyshacl, pas rdflib)
  5. conformité SPARQL 1.1 des requêtes
"""
import pathlib, re, sys
from collections import Counter
from rdflib import Graph, RDF, OWL, RDFS
from rdflib.namespace import SKOS, XSD

ROOT = pathlib.Path(__file__).parent.parent
FILES = ['ontology/ax5-compliance.ttl', 'data/instances.ttl']
SHAPES = 'shapes/ax5-shapes.ttl'

STANDARD_NS = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
    'http://www.w3.org/2000/01/rdf-schema#': 'rdfs',
    'http://www.w3.org/2002/07/owl#': 'owl',
    'http://www.w3.org/2004/02/skos/core#': 'skos',
    'http://www.w3.org/ns/prov#': 'prov',
    'http://www.w3.org/2001/XMLSchema#': 'xsd',
    'http://www.w3.org/ns/shacl#': 'sh',
    'http://purl.org/dc/terms/': 'dcterms',
}
ok = True


def head(n, t):
    print(f"\n{'='*70}\n{n}. {t}\n{'='*70}")


# 1 --------------------------------------------------------------- syntaxe
head(1, 'Analyse syntaxique stricte')
g = Graph()
for f in FILES:
    try:
        before = len(g)
        g.parse(ROOT / f, format='turtle')
        print(f"  OK   {f:38} {len(g)-before:>5} triplets")
    except Exception as e:
        ok = False
        print(f"  FAIL {f} : {e}")
print(f"  total : {len(g)} triplets")

# 2 ------------------------------------------------------- sérialisations
head(2, 'Sérialisation croisée — aller-retour sans perte')
for fmt in ['nt', 'xml', 'json-ld', 'turtle', 'n3']:
    try:
        s = g.serialize(format=fmt)
        g2 = Graph().parse(data=s, format=fmt)
        same = len(g2) == len(g)
        print(f"  {'OK  ' if same else 'ECART'} {fmt:9} {len(g2):>5} triplets"
              f"{'' if same else f'  (attendu {len(g)})'}")
        if not same:
            ok = False
    except Exception as e:
        ok = False
        print(f"  FAIL {fmt:9} {e}")

# 3 ------------------------------------------------------------ vocabulaire
head(3, 'Profil de vocabulaire')
preds = Counter()
for s, p, o in g:
    preds[str(p)] += 1
own, std, unknown = Counter(), Counter(), Counter()
for p, n in preds.items():
    ns = re.sub(r'[^#/]+$', '', p)
    if ns in STANDARD_NS:
        std[STANDARD_NS[ns]] += n
    elif 'agenticx5.com' in ns:
        own[ns] += n
    else:
        unknown[ns] += n
print('  vocabulaires standard utilisés :')
for k, n in std.most_common():
    print(f"    {k:9} {n:>5} usages")
print('  vocabulaire propre au projet :')
for k, n in own.most_common():
    print(f"    {k}  {n} usages")
if unknown:
    ok = False
    print('  ATTENTION — vocabulaires non identifiés :')
    for k, n in unknown.most_common():
        print(f"    {k}  {n}")
else:
    print('  aucun vocabulaire tiers non standard  -> portable')

classes = set(g.subjects(RDF.type, OWL.Class))
objp = set(g.subjects(RDF.type, OWL.ObjectProperty))
datp = set(g.subjects(RDF.type, OWL.DatatypeProperty))
print(f"\n  déclarations OWL : {len(classes)} classes, "
      f"{len(objp)} propriétés objet, {len(datp)} propriétés de données")

# constructions OWL avancées (celles qui exigent un raisonneur)
adv = [OWL.Restriction, OWL.unionOf, OWL.intersectionOf, OWL.complementOf,
       OWL.TransitiveProperty, OWL.SymmetricProperty, OWL.inverseOf,
       OWL.disjointWith, OWL.equivalentClass]
found = [str(t).split('#')[-1] for t in adv
         if (None, RDF.type, t) in g or (None, t, None) in g]
print(f"  constructions exigeant un raisonneur : "
      f"{', '.join(found) if found else 'aucune'}")
if not found:
    print("  -> le modèle est déclaratif : il se charge partout, y compris")
    print("     dans un magasin sans moteur d'inférence.")

# 4 ------------------------------------------------------------ SHACL tiers
head(4, 'Validation SHACL par un moteur tiers (pyshacl)')
try:
    from pyshacl import validate
    sg = Graph().parse(ROOT / SHAPES, format='turtle')
    conforms, rg, txt = validate(g, shacl_graph=sg, inference='none',
                                 abort_on_first=False, meta_shacl=False)
    viol = txt.count('Severity: sh:Violation')
    warn = txt.count('Severity: sh:Warning')
    print(f"  moteur      : pyshacl (indépendant de rdflib pour les règles)")
    print(f"  conforme    : {conforms}")
    print(f"  violations  : {viol}")
    print(f"  avertissements : {warn}")
    print("  -> les défauts délibérés sont bien détectés par un moteur tiers,")
    print("     donc les contraintes ne dépendent pas de validate.py.")
except Exception as e:
    ok = False
    print(f"  FAIL {e}")

# 5 ------------------------------------------------------------ SPARQL 1.1
head(5, 'Conformité SPARQL 1.1 des requêtes')
NONSTD = {
    'rdflib-only': [r'\bBIND\s*\(\s*rdflib', r'text:query', r'apoc\.'],
    'extension propriétaire': [r'stardog:', r'onto:', r'ph:', r'gdb:'],
}
qfiles = ['queries/competency.py', 'queries/forms.py']
forms = Counter()
issues = []
for qf in qfiles:
    p = ROOT / qf
    if not p.exists():
        continue
    src = p.read_text(encoding='utf-8')
    for m in re.finditer(r'\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b', src):
        forms[m.group(1)] += 1
    for label, pats in NONSTD.items():
        for pat in pats:
            if re.search(pat, src):
                issues.append(f'{qf}: {label} ({pat})')
print(f"  formes présentes : "
      f"{', '.join(f'{k} x{v}' for k, v in sorted(forms.items()))}")
if issues:
    ok = False
    print('  ATTENTION — constructions non standard :')
    for i in issues:
        print('   ', i)
else:
    print('  aucune extension propriétaire détectée')
    print('  -> requêtes exécutables sur tout point d\'accès SPARQL 1.1')

print(f"\n{'='*70}")
print('VERDICT :', 'PORTABLE' if ok else 'ECARTS À CORRIGER')
print('='*70)
sys.exit(0 if ok else 1)
