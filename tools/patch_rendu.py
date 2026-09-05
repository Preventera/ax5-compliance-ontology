#!/usr/bin/env python3
"""
Applique les correctifs de la doctrine de rendu OntoX5 à ax5-explorer/index.html.

Couvre R1 (second canal sur les états), R3 (compteurs qualifiés),
R10 (nom accessible sur les contrôles) et R11 (impression, noir et blanc).
Ne couvre pas R2 ni R8, qui demandent une décision humaine.

    python tools/patch_rendu.py            # applique, avec sauvegarde .bak
    python tools/patch_rendu.py --dry-run  # montre ce qui serait fait
    python tools/patch_rendu.py --restore  # revient à la sauvegarde

Le script est idempotent : relancé, il ne double aucune insertion.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CIBLE = RACINE / "ax5-explorer" / "index.html"
SAUVEGARDE = CIBLE.with_suffix(".html.bak")

MARQUEUR = "/* ontox5-rendu: patch applique */"

# ---------------------------------------------------------------------------
# R10 — nom accessible sur les quatre contrôles anonymes
# ---------------------------------------------------------------------------

CONTROLES = {
    "tgl": ("aTgl", "Afficher ou masquer le tableau", "Show or hide the table"),
    "qPick": ("aQPick", "Choisir une requête SPARQL", "Choose a SPARQL query"),
    "cFam": ("aCFam", "Filtrer par famille de concepts", "Filter by concept family"),
    "cQ": ("aCQ", "Rechercher un concept", "Search for a concept"),
}

# ---------------------------------------------------------------------------
# R3 — le bandeau de compteurs porte son dénominateur, sa source et sa date
# ---------------------------------------------------------------------------

ATTRS_COMPTEUR = {
    "data-denominator": "0",
    "data-source": "data/instances.ttl",
    "data-asof": "",
}

# ---------------------------------------------------------------------------
# CSS (R1 à l'écran + R11 à l'impression)
# ---------------------------------------------------------------------------

CSS = """
/* ======================================================================
   """ + MARQUEUR + """
   R1 : aucun état porté par la couleur seule.
   R11 : survit au noir et blanc et à l'impression.
   ====================================================================== */

#s-sparql .qbool b::before{font-family:var(--serif);margin-right:.35em;font-weight:700}
#s-sparql .qbool.no  b::before{content:"\\2717"}
#s-sparql .qbool.yes b::before{content:"\\2713"}

.sev::before,.pb::before{margin-right:.35em;font-weight:700}
.sev.v::before{content:"\\25B2"}
.sev.w::before{content:"\\25CF"}
.pb.human::before{content:"\\2713"}
.pb.machine::before,.badge.machine::before{content:"\\25C7"}

@media print{
  :root{--ink:#000;--muted:#333;--rule:#000;--rule2:#666;--sunk:#fff;
        --oxide:#000;--verdigris:#000}
  body{background:#fff;color:#000;font-size:10pt;line-height:1.45}
  @page{margin:15mm}
  .sev,.pb,.badge,.pill,.hstat span{border:1pt solid #000;background:none;padding:0 3pt}
  details{display:block}
  details>summary{display:none}
  .qttl,.qlimit,.lineage,.iwhy{overflow:visible;white-space:pre-wrap}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:8pt;color:#333;word-break:break-all}
  .skip,button,select,nav{display:none}
  .mark{filter:grayscale(1)}
  .card,.fiche,#insp>*{break-inside:avoid}
}
"""

# ---------------------------------------------------------------------------
# JS — application des aria-label à chaque changement de langue
# ---------------------------------------------------------------------------

JS = """
/* ontox5-rendu : R10 — les noms accessibles suivent la langue */
function applyAria(l){
  document.querySelectorAll('[data-i18n-aria]').forEach(function(el){
    var k = el.getAttribute('data-i18n-aria');
    if (T[l] && T[l][k]) el.setAttribute('aria-label', T[l][k]);
  });
}
if (typeof setLang === 'function') {
  var _setLangBase = setLang;
  setLang = function(l){ _setLangBase(l); applyAria(l); };
}
"""


def journal(actions: list[str], texte: str) -> None:
    actions.append(texte)


def patch_controles(html: str, actions: list[str]) -> str:
    """Ajoute aria-label et data-i18n-aria sur les contrôles listés."""
    for ident, (cle, fr, _en) in CONTROLES.items():
        motif = re.compile(rf"""<(button|select|input)\b([^>]*\bid=["']{ident}["'][^>]*)>""")
        m = motif.search(html)
        if not m:
            journal(actions, f"R10 · #{ident} introuvable, ignoré")
            continue
        if "data-i18n-aria" in m.group(2):
            journal(actions, f"R10 · #{ident} déjà nommé")
            continue
        ajout = f' aria-label="{fr}" data-i18n-aria="{cle}"'
        html = html[: m.end(2)] + ajout + html[m.end(2) :]
        journal(actions, f"R10 · #{ident} → aria-label + data-i18n-aria=\"{cle}\"")
    return html


def patch_compteur(html: str, actions: list[str]) -> str:
    """Ajoute dénominateur, source et date au bandeau .hstat."""
    m = re.search(r"""<div\b([^>]*\bclass=["'][^"']*\bhstat\b[^"']*["'][^>]*)>""", html)
    if not m:
        journal(actions, "R3 · aucun élément .hstat trouvé")
        return html
    if "data-denominator" in m.group(1):
        journal(actions, "R3 · .hstat déjà qualifié")
        return html
    ajout = "".join(f' {k}="{v}"' for k, v in ATTRS_COMPTEUR.items())
    html = html[: m.end(1)] + ajout + html[m.end(1) :]
    journal(actions, "R3 · .hstat → data-denominator, data-source, data-asof (à peupler)")
    return html


def patch_i18n(html: str, actions: list[str]) -> str:
    """Insère les clés aria dans les blocs fr et en de l'objet T."""
    for langue, indice in (("fr", 1), ("en", 2)):
        m = re.search(rf"(?<![\w$.]){langue}\s*:\s*\{{", html)
        if not m:
            journal(actions, f"R13 · bloc « {langue} » introuvable")
            continue
        pos = html.index("{", m.start()) + 1
        deja = [c for c, _f, _e in CONTROLES.values() if f"{c}:" in html[pos : pos + 4000]]
        if len(deja) == len(CONTROLES):
            journal(actions, f"R13 · clés aria déjà présentes dans « {langue} »")
            continue
        paires = ",".join(
            f"{cle}:{escape_js(fr if langue == 'fr' else en)}"
            for cle, fr, en in CONTROLES.values()
        )
        html = html[:pos] + paires + "," + html[pos:]
        journal(actions, f"R13 · {len(CONTROLES)} clés aria ajoutées dans « {langue} »")
    return html


def escape_js(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def patch_css(html: str, actions: list[str]) -> str:
    if MARQUEUR in html:
        journal(actions, "R1/R11 · CSS déjà présent")
        return html
    idx = html.rfind("</style>")
    if idx == -1:
        journal(actions, "R1/R11 · aucune balise </style>, CSS non inséré")
        return html
    journal(actions, "R1/R11 · CSS inséré avant </style>")
    return html[:idx] + CSS + html[idx:]


def patch_js(html: str, actions: list[str]) -> str:
    if "function applyAria" in html:
        journal(actions, "R10 · applyAria déjà présent")
        return html
    m = re.search(r"\n\s*setLang\((['\"])\w+\1\)\s*;", html)
    if not m:
        idx = html.rfind("</script>")
        if idx == -1:
            journal(actions, "R10 · impossible de placer applyAria")
            return html
        journal(actions, "R10 · applyAria inséré avant </script> (appel setLang non trouvé)")
        return html[:idx] + JS + html[idx:]
    journal(actions, "R10 · applyAria inséré avant l'appel setLang")
    return html[: m.start()] + "\n" + JS + html[m.start() :]


def principal() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="n'écrit rien")
    ap.add_argument("--restore", action="store_true", help="restaure la sauvegarde")
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
    html, actions = original, []

    html = patch_controles(html, actions)
    html = patch_compteur(html, actions)
    html = patch_i18n(html, actions)
    html = patch_js(html, actions)
    html = patch_css(html, actions)

    print(f"Cible : {CIBLE}")
    for a in actions:
        print("  " + a)

    if html == original:
        print("\nAucune modification nécessaire.")
        return 0

    if args.dry_run:
        print(f"\n[dry-run] {len(html) - len(original):+d} octets, rien écrit.")
        return 0

    if not SAUVEGARDE.exists():
        shutil.copy2(CIBLE, SAUVEGARDE)
        print(f"\nSauvegarde : {SAUVEGARDE.name}")
    CIBLE.write_text(html, encoding="utf-8")
    print(f"Écrit : {len(html) - len(original):+d} octets")
    print("\nReste à faire à la main :")
    print("  · peupler data-denominator / data-asof avec les vraies valeurs")
    print("  · R8 : reformuler ou exempter l'emploi de « conforme »")
    print("  · R2 : distinguer LACUNE de NON_EVALUE dans queries_couverture.py")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
