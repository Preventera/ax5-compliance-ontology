#!/usr/bin/env python3
"""
Correctif v2 de ax5-explorer/index.html — doctrine de rendu OntoX5.

Corrige quatre choses, dans l'ordre de gravité :

  1. BOGUE CSS  — le commentaire du patch v1 était imbriqué (/* ... /* ... */),
     ce qui refermait le commentaire trop tôt. Les huit règles de glyphes de R1
     n'ont donc JAMAIS été appliquées, et VS Code signalait 3 erreurs.
  2. DOUBLON    — deux blocs @media print concurrents. Le premier est retiré.
  3. R2         — LACUNE et NON_EVALUE deviennent deux états distincts,
     dérivés des données : une obligation sans revendication dans un régime
     où AUCUN document interne n'existe n'est pas une lacune, c'est une
     absence d'évaluation. Sur ce jeu, ISO 45001 §5.4 bascule en non évalué.
  4. R3         — covbar porte son dénominateur, sa source et sa date ; hstat
     et covbar sont peuplés à l'exécution au lieu de rester à zéro.

    python tools/patch_rendu2.py --dry-run
    python tools/patch_rendu2.py
    python tools/patch_rendu2.py --restore

Idempotent : relancé, il ne double rien.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

CIBLE = Path(__file__).resolve().parents[1] / "ax5-explorer" / "index.html"
SAUVEGARDE = CIBLE.with_suffix(".html.bak2")
MARQUEUR = "ontox5-rendu v2"


# ---------------------------------------------------------------------------
# 1. Bogue de commentaire CSS imbriqué
# ---------------------------------------------------------------------------

COMMENTAIRE_CASSE = """/* ======================================================================
   /* ontox5-rendu: patch applique */
   R1 : aucun état porté par la couleur seule.
   R11 : survit au noir et blanc et à l'impression.
   ====================================================================== */"""

COMMENTAIRE_SAIN = """/* ==== ontox5-rendu v2 =================================================
   R1  : aucun etat porte par la couleur seule (glyphe + libelle).
   R2  : LACUNE et NON_EVALUE ont deux rendus distincts.
   R11 : survit au noir et blanc et a l'impression.
   ===================================================================== */"""


# ---------------------------------------------------------------------------
# 2. Ancien bloc @media print, devenu redondant
# ---------------------------------------------------------------------------

VIEUX_PRINT = re.compile(
    r"/\* ---- R11 : survit au noir et blanc et à l'impression ---- \*/\n"
    r"@media print\{.*?\n\}\n\n",
    re.S,
)


# ---------------------------------------------------------------------------
# 3. CSS additionnel : glyphes manquants + état « non évalué »
# ---------------------------------------------------------------------------

CSS_SUP = """
/* R1 — le oui/non de la console de cas ne peut pas non plus tenir a la couleur */
#s-cases .cbool b::before{margin-right:.35em;font-weight:700}
#s-cases .cbool.no  b::before{content:"\\2717"}
#s-cases .cbool.yes b::before{content:"\\2713"}

/* R2 — trois absences, trois rendus. Le disque plein signale une lacune
   reelle ; le cercle vide signale que le systeme n'a pas regarde. */
.gap .g-title::before{content:"\\25CF";margin-right:.45em;color:var(--ochre)}
.noneval{background:var(--sunk);border:1px dashed var(--rule2);
  border-left:3px dashed var(--dim);border-radius:3px;padding:14px 17px;margin-top:10px}
.noneval .g-title{font-family:var(--display);font-size:14.5px;font-weight:500;color:var(--ink)}
.noneval .g-title::before{content:"\\25CB";margin-right:.45em;color:var(--dim)}
.noneval .g-cite{font-family:var(--data);font-size:12px;color:var(--dim);margin-top:4px}
.noneval .g-why{font-size:13px;color:var(--muted);margin-top:8px;line-height:1.55}
.covbar .noneval-n b{color:var(--dim)}
"""

CSS_PRINT_SUP = """  .noneval{border:1pt dashed #000;background:none}
"""


# ---------------------------------------------------------------------------
# 4. HTML : covbar qualifie
# ---------------------------------------------------------------------------

COVBAR_AV = '<div class="covbar" id="covbar"></div>'
COVBAR_AP = (
    '<div class="covbar" id="covbar"\n'
    '           data-denominator="0" data-source="data/instances.ttl" data-asof=""></div>'
)


# ---------------------------------------------------------------------------
# 5. JS : date de reference derivee des donnees
# ---------------------------------------------------------------------------

ETAT_AV = "let lang='fr', anchor='ri', sel=null, tblOpen=false;"
ETAT_AP = """let lang='fr', anchor='ri', sel=null, tblOpen=false;

/* R3 — la date affichee n'est pas celle du navigateur mais celle de la
   derniere assertion du jeu de donnees. Un compteur sans date ne dit pas
   de quand il parle. */
const AS_OF = [].concat(
  COVS.map(function(c){return c.date}),
  MAPS.map(function(m){return m.date})
).filter(Boolean).sort().pop() || '';
const SOURCE = 'data/instances.ttl';"""


# ---------------------------------------------------------------------------
# 6. JS : LACUNE vs NON_EVALUE
# ---------------------------------------------------------------------------

TROUS_AV = """  const trous = reqsA.filter(r=>!couvertes.has(r.id));
  const nonRevues = cvs.filter(c=>c.status!=='human-reviewed');"""

TROUS_AP = """  /* R2 — trois situations, pas deux.
     Une obligation sans revendication dans un regime ou AUCUN document
     interne n'existe n'est pas une lacune : le systeme n'a pas regarde.
     Confondre les deux produit une fausse assurance. */
  const regimesDocumentes = new Set(DOCS.map(d=>d.jur));
  const sansClaim = reqsA.filter(r=>!couvertes.has(r.id));
  const trous   = sansClaim.filter(r=>regimesDocumentes.has(r.jur));
  const nonEval = sansClaim.filter(r=>!regimesDocumentes.has(r.jur));
  const nonRevues = cvs.filter(c=>c.status!=='human-reviewed');"""


COVBAR_JS_AV = """  covbar.innerHTML = `
    <div><b>${reqsA.length}</b>${t('cTotal')}</div>
    <div><b>${couvertes.size}</b>${t('cCouv')}</div>
    <div class="gap"><b>${trous.length}</b>${t('cGap')}</div>
    <div class="unrev"><b>${nonRevues.length}</b>${t('cUnrev')}</div>`;"""

COVBAR_JS_AP = """  covbar.dataset.denominator = reqsA.length;
  covbar.dataset.source = SOURCE;
  covbar.dataset.asof = AS_OF;
  covbar.innerHTML = `
    <div><b>${reqsA.length}</b>${t('cTotal')}</div>
    <div><b>${couvertes.size}</b>${t('cCouv')}</div>
    <div class="gap"><b>${trous.length}</b>${t('cGap')}</div>
    <div class="noneval-n"><b>${nonEval.length}</b>${t('cNonEval')}</div>
    <div class="unrev"><b>${nonRevues.length}</b>${t('cUnrev')}</div>`;"""


COVS_AV = """  covs.innerHTML =
    trous.map(r=>`<div class="gap">"""

COVS_AP = """  covs.innerHTML =
    nonEval.map(r=>`<div class="noneval">
      <div class="g-title">${esc(r.label[lang])}</div>
      <div class="g-cite">${r.cite?esc(r.cite):'\\u26a0 '+t('noCite')} \\u00b7 ${esc(JUR[r.jur])} \\u00b7 ${t('cNonEvalLbl')}</div>
      <div class="g-why">${t('nonEvalWhy')}</div>
    </div>`).join('') +
    trous.map(r=>`<div class="gap">"""


# ---------------------------------------------------------------------------
# 7. JS : hstat peuple
# ---------------------------------------------------------------------------

HSTAT_AV = "function render(){\n  const counts = {};"
HSTAT_AP = """function render(){
  /* R3 — le bandeau de tete dit sur quoi il compte et de quand il parle. */
  const hs = document.querySelector('.hstat');
  if(hs){
    hs.dataset.denominator = CONCEPTS.length + MAPS.length + REQS.length + COVS.length;
    hs.dataset.source = SOURCE;
    hs.dataset.asof = AS_OF;
  }
  const counts = {};"""


# ---------------------------------------------------------------------------
# 8. i18n
# ---------------------------------------------------------------------------

I18N_FR_AV = "  cTotal:'obligations', cCouv:'couvertes', cGap:'sans couverture', cUnrev:'non revues',"
I18N_FR_AP = (
    "  cTotal:'obligations', cCouv:'couvertes', cGap:'sans couverture', cUnrev:'non revues',\n"
    "  cNonEval:'non évaluées', cNonEvalLbl:'Non évalué',\n"
    "  kNonEval:'Obligation non évaluée',\n"
    "  nonEvalWhy:\"Aucun document interne n'existe pour ce régime. Le système n'a pas \"+\n"
    "    \"cherché : ce n'est ni une lacune ni une conformité, c'est une absence \"+\n"
    "    \"d'évaluation. Un trou de couverture engage le client; un non-évalué engage \"+\n"
    "    \"le corpus. Les confondre produit une fausse assurance.\","
)

I18N_EN_AV = "  cTotal:'obligations', cCouv:'covered', cGap:'uncovered', cUnrev:'unreviewed',"
I18N_EN_AP = (
    "  cTotal:'obligations', cCouv:'covered', cGap:'uncovered', cUnrev:'unreviewed',\n"
    "  cNonEval:'not evaluated', cNonEvalLbl:'Not evaluated',\n"
    "  kNonEval:'Obligation not evaluated',\n"
    "  nonEvalWhy:'No internal document exists for this regime. The system did not '+\n"
    "    'look: this is neither a gap nor compliance, it is an absence of evaluation. '+\n"
    "    'A coverage gap implicates the client; a not-evaluated implicates the corpus. '+\n"
    "    'Conflating them produces false assurance.',"
)


# ---------------------------------------------------------------------------

EDITIONS: list[tuple[str, str, str]] = [
    ("CSS · commentaire imbriqué corrigé", COMMENTAIRE_CASSE, COMMENTAIRE_SAIN),
    ("HTML · covbar qualifié (R3)", COVBAR_AV, COVBAR_AP),
    ("JS · AS_OF et SOURCE dérivés des données", ETAT_AV, ETAT_AP),
    ("JS · LACUNE distinguée de NON_EVALUE (R2)", TROUS_AV, TROUS_AP),
    ("JS · covbar peuplé + 5e compteur", COVBAR_JS_AV, COVBAR_JS_AP),
    ("JS · rendu des obligations non évaluées", COVS_AV, COVS_AP),
    ("JS · hstat peuplé (R3)", HSTAT_AV, HSTAT_AP),
    ("i18n · clés fr", I18N_FR_AV, I18N_FR_AP),
    ("i18n · clés en", I18N_EN_AV, I18N_EN_AP),
]


def appliquer(html: str) -> tuple[str, list[str]]:
    actions: list[str] = []

    if MARQUEUR in html:
        return html, ["déjà appliqué (marqueur présent)"]

    m = VIEUX_PRINT.search(html)
    if m:
        html = html[: m.start()] + html[m.end() :]
        actions.append("CSS · ancien bloc @media print retiré (doublon)")
    else:
        actions.append("CSS · ancien bloc @media print introuvable, ignoré")

    for libelle, avant, apres in EDITIONS:
        n = html.count(avant)
        if n == 0:
            actions.append(f"!! {libelle} — ancre introuvable, IGNORÉ")
            continue
        if n > 1:
            actions.append(f"!! {libelle} — ancre ambiguë ({n} fois), IGNORÉ")
            continue
        html = html.replace(avant, apres, 1)
        actions.append(libelle)

    # CSS supplémentaire, inséré juste après le commentaire sain
    if COMMENTAIRE_SAIN in html and CSS_SUP.strip() not in html:
        html = html.replace(COMMENTAIRE_SAIN, COMMENTAIRE_SAIN + CSS_SUP, 1)
        actions.append("CSS · glyphes .cbool, .gap, .noneval ajoutés")

    # règle d'impression pour le nouvel état
    cible = "  .card,.fiche,#insp>*{break-inside:avoid}\n"
    if cible in html and ".noneval{border:1pt dashed" not in html:
        html = html.replace(cible, CSS_PRINT_SUP + cible, 1)
        actions.append("CSS · .noneval traité à l'impression")

    return html, actions


def principal() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not SAUVEGARDE.exists():
            print(f"Aucune sauvegarde : {SAUVEGARDE}")
            return 1
        shutil.copy2(SAUVEGARDE, CIBLE)
        print(f"Restauré depuis {SAUVEGARDE.name}")
        return 0

    if not CIBLE.exists():
        print(f"Fichier introuvable : {CIBLE}")
        return 1

    original = CIBLE.read_text(encoding="utf-8")
    html, actions = appliquer(original)

    print(f"Cible : {CIBLE}")
    for a in actions:
        print("  " + a)

    rates = [a for a in actions if a.startswith("!!")]
    if rates:
        print(f"\n{len(rates)} ancre(s) introuvable(s). Le fichier a-t-il été édité à la main ?")

    if html == original:
        print("\nAucune modification.")
        return 0
    if args.dry_run:
        print(f"\n[dry-run] {len(html) - len(original):+d} octets, rien écrit.")
        return 0

    if not SAUVEGARDE.exists():
        shutil.copy2(CIBLE, SAUVEGARDE)
        print(f"\nSauvegarde : {SAUVEGARDE.name}")
    CIBLE.write_text(html, encoding="utf-8")
    print(f"Écrit : {len(html) - len(original):+d} octets")
    return 0 if not rates else 2


if __name__ == "__main__":
    sys.exit(principal())
