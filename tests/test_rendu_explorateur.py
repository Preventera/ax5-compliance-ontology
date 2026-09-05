"""
Contrôle mécanique de la doctrine de rendu OntoX5.

Contrepartie visuelle de validate.py : les shapes SHACL disent ce qu'une
donnée doit porter, ce fichier dit ce qu'un écran doit porter.

Chaque test nomme la règle de SKILL.md qu'il fait échouer. Aucune
dépendance hors bibliothèque standard.

    pytest tests/test_rendu_explorateur.py -v
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# CONFIG — la seule section à ajuster aux noms de classes réels du projet.
# --------------------------------------------------------------------------

CIBLE = Path(__file__).resolve().parents[1] / "ax5-explorer" / "index.html"

# Classes portant un état de validation, de couverture ou de revue (R1).
# Renseigné d'après les classes réelles de ax5-explorer/index.html.
CLASSES_ETAT = ("sev", "pb", "qbool", "badge", "pill", "state")

# Classes portant un nombre agrégé (R3). `hstat` est le bandeau de tête
# qui affiche le nombre de violations et d'avertissements.
CLASSES_COMPTEUR = ("hstat", "covbar", "kpi", "metric", "count")

# Paires (avant-plan, arrière-plan) à vérifier en contraste (R9).
# Renseigner avec les noms de variables CSS réels ; le test liste les
# variables découvertes tant que cette liste est vide.
PAIRES_CONTRASTE: list[tuple[str, str, float]] = [
    ("--ink", "--sunk", 4.5),
    ("--muted", "--sunk", 4.5),
    ("--oxide", "--sunk", 4.5),
    ("--verdigris", "--sunk", 4.5),
]

# Occurrences de MOTS_VERDICT légitimes : le lexique explique justement ce
# que le modèle refuse de dire. Motifs regex testés sur le contexte.
EXEMPTIONS_VERDICT: tuple[str, ...] = (
    r'"q[fe]"\s*:',
    r'"c[fe]"\s*:',
    r'"st"\s*:',
    r"<strong>",
    r"declare compliant what is not",
    r"perfectly compliant in Qu",
)

# Verdicts de conformité interdits (R8). Motifs regex, pas des mots isolés :
# « ontologie de conformité » est légitime, « est conforme » ne l'est pas.
MOTS_VERDICT = (r"est\s+conforme", r"non[\s-]+conformes?", r"\bcompliant\b")

DUREE_TRANSITION_MAX_MS = 200


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def html() -> str:
    if not CIBLE.exists():
        pytest.fail(f"Fichier introuvable : {CIBLE}")
    return CIBLE.read_text(encoding="utf-8")


class Collecteur(HTMLParser):
    """Collecte les éléments avec leurs attributs et leur texte propre."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[dict] = []
        self._pile: list[dict] = []

    def handle_starttag(self, tag, attrs):
        el = {
            "tag": tag,
            "attrs": dict(attrs),
            "texte": "",
            "enfants": [],
        }
        if self._pile:
            self._pile[-1]["enfants"].append(el)
        self.elements.append(el)
        if tag not in ("br", "img", "input", "meta", "link", "hr", "path", "use"):
            self._pile.append(el)

    def handle_endtag(self, tag):
        for i in range(len(self._pile) - 1, -1, -1):
            if self._pile[i]["tag"] == tag:
                del self._pile[i:]
                break

    def handle_data(self, data):
        if self._pile and data.strip():
            self._pile[-1]["texte"] += data


@pytest.fixture(scope="module")
def dom(html: str) -> list[dict]:
    c = Collecteur()
    c.feed(html)
    return c.elements


def classes(el: dict) -> set[str]:
    return set((el["attrs"].get("class") or "").split())


def a_une_classe(el: dict, prefixes: tuple[str, ...]) -> bool:
    return any(cl == p or cl.startswith(p) for cl in classes(el) for p in prefixes)


def texte_profond(el: dict) -> str:
    out = el["texte"]
    for enfant in el["enfants"]:
        out += texte_profond(enfant)
    return out.strip()


def a_un_glyphe(el: dict) -> bool:
    """Second canal non textuel : icône, svg, forme, ou attribut de forme."""
    if el["attrs"].get("data-shape") or el["attrs"].get("data-glyph"):
        return True
    for enfant in el["enfants"]:
        if enfant["tag"] in ("svg", "symbol", "use"):
            return True
        if a_une_classe(enfant, ("ic", "icon", "glyph", "shape")):
            return True
        if a_un_glyphe(enfant):
            return True
    return False


def blocs_style(html: str) -> str:
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))


def bloc_script(html: str) -> str:
    return "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S | re.I))


def _luminance(hexa: str) -> float:
    h = hexa.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contraste(fg: str, bg: str) -> float:
    l1, l2 = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def palette(html: str) -> dict[str, str]:
    return {
        f"--{nom}": val
        for nom, val in re.findall(
            r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;", blocs_style(html)
        )
    }


def cles_niveau_un(bloc: str) -> set[str]:
    """Clés au premier niveau d'un littéral objet JS, hors chaînes."""
    cles: set[str] = set()
    prof, i, n = 0, 0, len(bloc)
    guillemet = None
    courant = ""
    while i < n:
        c = bloc[i]
        if guillemet:
            if c == "\\":
                i += 2
                continue
            if c == guillemet:
                guillemet = None
            i += 1
            continue
        if c in "\"'`":
            guillemet = c
            courant = ""
        elif c in "{[(":
            prof += 1
            courant = ""
        elif c in "}])":
            prof -= 1
            courant = ""
        elif c == ":" and prof == 1 and courant.strip():
            cles.add(courant.strip().strip("\"'"))
            courant = ""
        elif c == ",":
            courant = ""
        else:
            courant += c
        i += 1
    return {k for k in cles if re.fullmatch(r"[\w-]+", k)}


def bloc_apres(texte: str, cle: str) -> str:
    """Bloc { } d'une declaration `cle:` reelle, pas d'une sous-chaine.

    `texte.find("en:")` s'accroche a n'importe quel `en:` du script, y
    compris a l'interieur d'un identifiant. Le lookbehind l'empeche.
    """
    m = re.search(rf"(?<![\w$.]){re.escape(cle)}\s*:\s*\{{", texte)
    if not m:
        return ""
    debut = texte.index("{", m.start())
    prof, i = 0, debut
    while i < len(texte):
        if texte[i] == "{":
            prof += 1
        elif texte[i] == "}":
            prof -= 1
            if prof == 0:
                return texte[debut : i + 1]
        i += 1
    return ""


# --------------------------------------------------------------------------
# R1 — aucun état porté par la couleur seule
# --------------------------------------------------------------------------


def test_r1_etats_a_deux_canaux(dom):
    fautifs = []
    for el in dom:
        if not a_une_classe(el, CLASSES_ETAT):
            continue
        if not texte_profond(el) and not a_un_glyphe(el):
            fautifs.append(f"<{el['tag']} class=\"{el['attrs'].get('class')}\">")
    assert not fautifs, (
        "R1 — état porté par la couleur seule, sans libellé ni glyphe :\n  "
        + "\n  ".join(sorted(set(fautifs)))
    )


# --------------------------------------------------------------------------
# R2 — le vide, le zéro et l'inconnu ne se ressemblent pas
# --------------------------------------------------------------------------


def test_r2_tiret_cadratin_toujours_qualifie(html):
    """Un « — » seul dans une cellule ne dit pas s'il s'agit d'un vide,
    d'un zéro mesuré ou d'un non-évalué."""
    nus = re.findall(r">\s*(?:—|–|-{1,2})\s*<", html)
    assert not nus, (
        f"R2 — {len(nus)} tiret(s) nu(s) employé(s) comme valeur. "
        "Qualifier : « non évalué », « aucune correspondance », « 0 mesuré »."
    )


def test_r2_etat_non_evalue_existe(html):
    """L'ignorance du système doit avoir un rendu nommé, pas un gris pâle."""
    marqueurs = ("non évalué", "non evalue", "not evaluated", "NON_EVALUE")
    assert any(m.lower() in html.lower() for m in marqueurs), (
        "R2 — aucun état « non évalué » repérable. LACUNE et NON_EVALUE "
        "sont indistinguables à l'écran."
    )


# --------------------------------------------------------------------------
# R3 — aucun compteur sans dénominateur, source et date
# --------------------------------------------------------------------------


def test_r3_compteurs_qualifies(dom):
    manquants = []
    for el in dom:
        if not a_une_classe(el, CLASSES_COMPTEUR):
            continue
        for attr in ("data-denominator", "data-source", "data-asof"):
            if attr not in el["attrs"]:
                manquants.append(f"{el['attrs'].get('class')} → {attr}")
    assert not manquants, (
        "R3 — compteur sans dénominateur, source ou date :\n  "
        + "\n  ".join(sorted(set(manquants)))
    )


# --------------------------------------------------------------------------
# R4 — provenance au premier niveau de lecture
# --------------------------------------------------------------------------


def test_r4_provenance_non_repliee(html):
    """Base, auteur, statut et date ne vivent pas dans un <details>."""
    for bloc in re.findall(r"<details[^>]*>(.*?)</details>", html, re.S | re.I):
        for champ in ("basis", "author", "wasAttributedTo", "reviewStatus"):
            assert champ not in bloc, (
                f"R4 — le champ de provenance « {champ} » est replié dans "
                "un <details>. EXPLICITATION = 9 exige la visibilité directe."
            )


# --------------------------------------------------------------------------
# R5 — l'ancre n'est jamais une réponse
# --------------------------------------------------------------------------


def test_r5_ancre_non_titre(html):
    titres = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, re.S | re.I)
    for t in titres:
        assert "anchor" not in t.lower() and "ancre" not in t.lower(), (
            "R5 — l'AnchorConcept apparaît en titre de niveau 1 ou 2. "
            "L'ancre est une entrée d'index, pas une réponse."
        )


# --------------------------------------------------------------------------
# R6 / R7 — exactMatch vs closeMatch, machine vs humain
# --------------------------------------------------------------------------


def test_r6_seuil_exactmatch_affiche(html):
    assert "0.95" in html or "0,95" in html, (
        "R6 — le seuil de 0,95 qui sépare exactMatch de closeMatch n'apparaît "
        "nulle part. L'utilisateur ne peut pas situer la confiance affichée."
    )


def test_r7_machine_et_humain_distincts(html):
    style = blocs_style(html)
    a_humain = re.search(r"\.(human|revue|reviewed)\b", style)
    a_machine = re.search(r"\.(machine|proposed|propose)\b", style)
    assert a_humain and a_machine, (
        "R7 — aucune règle de style distincte pour « revue humaine » et "
        "« proposé par machine ». Une nuance de la même pastille ne suffit pas."
    )


# --------------------------------------------------------------------------
# R8 — le mot « conforme » est banni hors lexique
# --------------------------------------------------------------------------


def test_r8_aucun_verdict_de_conformite(html):
    """Le verdict appartient à l'humain. L'écran dit ce que la contrainte
    dit — « satisfait MAP-006 » — pas « conforme »."""
    trouves = []
    for motif in MOTS_VERDICT:
        for m in re.finditer(motif, html, re.I):
            contexte = html[max(0, m.start() - 90) : m.end() + 90]
            contexte = " ".join(contexte.split())
            if any(re.search(ex, contexte, re.I) for ex in EXEMPTIONS_VERDICT):
                continue
            ligne = html[: m.start()].count("\n") + 1
            trouves.append(f"L{ligne} : …{contexte}…")
    assert not trouves, (
        "R8 — verdict de conformité employé :\n  " + "\n  ".join(trouves) + "\n"
        "Reformuler, ou ajouter un motif à EXEMPTIONS_VERDICT si l'emploi "
        "est explicatif."
    )


# --------------------------------------------------------------------------
# R9 — contraste AA
# --------------------------------------------------------------------------


def test_r9_contraste_aa(html):
    pal = palette(html)
    inventaire = "\n  ".join(f"{k} = {v}" for k, v in sorted(pal.items()))
    if not PAIRES_CONTRASTE:
        pytest.skip("R9 — PAIRES_CONTRASTE vide. Palette :\n  " + inventaire)

    absents = sorted(
        {v for fg, bg, _ in PAIRES_CONTRASTE for v in (fg, bg) if v not in pal}
    )
    if absents:
        pytest.skip(
            f"R9 — variables introuvables : {absents}\n"
            "Ajuster PAIRES_CONTRASTE. Palette :\n  " + inventaire
        )

    echecs = []
    for fg, bg, seuil in PAIRES_CONTRASTE:
        ratio = contraste(pal[fg], pal[bg])
        if ratio < seuil:
            echecs.append(f"{fg} sur {bg} = {ratio:.2f}:1 (exigé {seuil}:1)")
    assert not echecs, "R9 — contraste insuffisant :\n  " + "\n  ".join(echecs)


# --------------------------------------------------------------------------
# R10 — clavier et lecteur d'écran
# --------------------------------------------------------------------------


def test_r10_focus_visible(html):
    style = blocs_style(html)
    assert ":focus-visible" in style or ":focus" in style, (
        "R10 — aucun style de focus. Navigation clavier invisible."
    )
    assert "outline:none" not in style.replace(" ", "") or ":focus" in style, (
        "R10 — outline supprimé sans style de focus de remplacement."
    )


def test_r10_inspecteur_annonce(html):
    assert "aria-live" in html, (
        "R10 — le changement de fiche dans l'inspecteur n'est pas annoncé. "
        "Ajouter aria-live=\"polite\" sur le conteneur."
    )


def test_r10_controles_nommes(dom):
    anonymes = []
    for el in dom:
        if el["tag"] not in ("button", "a", "select", "input"):
            continue
        a = el["attrs"]
        nomme = (
            texte_profond(el)
            or a.get("aria-label")
            or a.get("aria-labelledby")
            or a.get("title")
            or a.get("data-i18n")
        )
        if not nomme:
            anonymes.append(f"<{el['tag']} {a}>")
    assert not anonymes, (
        "R10 — contrôle sans nom accessible :\n  " + "\n  ".join(anonymes[:10])
    )


def test_r10_lang_et_lien_evitement(html):
    assert re.search(r"<html[^>]+lang=", html, re.I), "R10 — attribut lang absent."
    assert "skip" in html.lower(), "R10 — lien d'évitement absent."


# --------------------------------------------------------------------------
# R11 — survit au noir et blanc, MOUVEMENT = 1
# --------------------------------------------------------------------------


def test_r11_mouvement_contenu(html):
    style = blocs_style(html)
    assert "infinite" not in style, (
        "R11 / MOUVEMENT=1 — animation en boucle infinie. "
        "Rien n'est calculé dans cet écran, rien ne doit suggérer un calcul."
    )
    trop_longues = [
        d
        for d in re.findall(r"transition[^;]*?(\d+(?:\.\d+)?)m?s", style)
        if float(d) > DUREE_TRANSITION_MAX_MS
    ]
    assert not trop_longues, (
        f"R11 / MOUVEMENT=1 — transition(s) au-delà de "
        f"{DUREE_TRANSITION_MAX_MS} ms : {trop_longues}"
    )


def test_r11_mouvement_reduit_respecte(html):
    assert "prefers-reduced-motion" in blocs_style(html), (
        "R11 — prefers-reduced-motion non pris en charge."
    )


def test_r11_impression_prevue(html):
    assert "@media print" in blocs_style(html), (
        "R11 — aucune feuille d'impression. Le test terrain est le rapport "
        "imprimé en noir et blanc."
    )


# --------------------------------------------------------------------------
# R12 — l'export porte la provenance
# --------------------------------------------------------------------------


def test_r12_export_horodate_et_averti(html):
    js = bloc_script(html)
    assert "exportedAt" in js, "R12 — export sans horodatage."
    assert re.search(r"no compliance decision|aucune decision|aucune décision", js, re.I), (
        "R12 — export sans la mention qu'aucune décision de conformité "
        "n'est impliquée."
    )


# --------------------------------------------------------------------------
# R13 — parité linguistique
# --------------------------------------------------------------------------


def test_r13_parite_fr_en(html):
    js = bloc_script(html)
    fr = cles_niveau_un(bloc_apres(js, "fr"))
    en = cles_niveau_un(bloc_apres(js, "en"))
    if not fr or not en:
        pytest.skip("R13 — blocs fr/en introuvables ; ajuster bloc_apres().")
    manque_en, manque_fr = sorted(fr - en), sorted(en - fr)
    assert not manque_en and not manque_fr, (
        f"R13 — clés absentes de en : {manque_en}\n"
        f"      clés absentes de fr : {manque_fr}\n"
        "Une clé manquante rend un état vide, donc neutre : violation de R2."
    )


def test_r13_cles_data_i18n_declarees(html):
    js = bloc_script(html)
    fr = cles_niveau_un(bloc_apres(js, "fr"))
    if not fr:
        pytest.skip("R13 — bloc fr introuvable.")
    utilisees = set(re.findall(r'data-i18n="([\w-]+)"', html))
    orphelines = sorted(utilisees - fr)
    assert not orphelines, (
        f"R13 — clés data-i18n sans traduction : {orphelines}"
    )

# --------------------------------------------------------------------------
# R14 — le code produit est syntaxiquement valide, pas seulement present
# --------------------------------------------------------------------------


def _hors_chaine(css: str):
    """Parcourt le CSS en signalant la position des marqueurs de commentaire,
    en ignorant ce qui se trouve dans une chaine ou une URL."""
    i, n = 0, len(css)
    guillemet = None
    while i < n:
        c = css[i]
        if guillemet:
            if c == "\\":
                i += 2
                continue
            if c == guillemet:
                guillemet = None
            i += 1
            continue
        if c in "\"'":
            guillemet = c
            i += 1
            continue
        if css.startswith("/*", i):
            yield i, "ouvre"
            i += 2
            continue
        if css.startswith("*/", i):
            yield i, "ferme"
            i += 2
            continue
        i += 1


def test_r14_commentaires_css_non_imbriques(html):
    """Un commentaire CSS ne peut pas en contenir un autre. Imbriqué, il se
    referme trop tôt et tout ce qui suit est ignoré par le navigateur — sans
    la moindre erreur visible. C'est ainsi que R1 est resté au vert alors
    qu'aucun glyphe n'était rendu."""
    css = blocs_style(html)
    profondeur = 0
    for pos, quoi in _hors_chaine(css):
        ligne = css[:pos].count("\n") + 1
        if quoi == "ouvre":
            profondeur += 1
            assert profondeur <= 1, (
                f"R14 — commentaire CSS imbriqué à la ligne {ligne} du bloc "
                "<style>. Le commentaire englobant se referme au premier */ "
                "et les règles suivantes sont silencieusement ignorées."
            )
        else:
            profondeur -= 1
            assert profondeur >= 0, (
                f"R14 — */ sans /* correspondant à la ligne {ligne}."
            )
    assert profondeur == 0, "R14 — commentaire CSS non refermé."


def test_r14_accolades_css_equilibrees(html):
    """Une accolade manquante fait avaler les règles suivantes par le bloc
    précédent. Le fichier reste 'valide' pour un test de présence."""
    css = blocs_style(html)
    sans_com = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    sans_str = re.sub(r"\"[^\"]*\"|'[^']*'", "", sans_com)
    ouvertes, fermees = sans_str.count("{"), sans_str.count("}")
    assert ouvertes == fermees, (
        f"R14 — accolades déséquilibrées dans <style> : "
        f"{ouvertes} ouvrantes, {fermees} fermantes."
    )
