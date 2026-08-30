"""
POLITIQUE DE SÉVÉRITÉ
=====================

C'est le module le plus important du générateur, et le seul qui contienne
un vrai jugement d'architecte. Tout le reste est de la mécanique.

LA QUESTION
-----------
Une contrainte détecte un défaut. Que doit-il arriver ensuite ?

    Violation  -> le pipeline s'arrête, la donnée n'entre pas
    Warning    -> la donnée entre, le défaut est compté et rapporté
    Info       -> noté, sans suivi

Ce n'est PAS une échelle de gravité. C'est une décision d'aiguillage.
La bonne question n'est jamais « à quel point est-ce grave », c'est :

    « Que coûte le blocage, comparé à ce que coûte le passage ? »

LES TROIS TESTS
---------------
Pour chaque contrainte, on pose trois questions dans cet ordre.

  TEST 1 — Le défaut produit-il une réponse FAUSSE, ou seulement
           une réponse INCOMPLÈTE ?

      Fausse      -> Violation.
      Incomplète  -> continuer au test 2.

      Une exigence sans citation produit une réponse de conformité que
      personne ne peut vérifier : elle a l'air bonne et elle est
      inutilisable. C'est faux, pas incomplet.

      Une exigence sans danger rattaché est incomplète : la réponse
      qu'elle produit reste vraie, elle est juste moins bien indexée.

  TEST 2 — Une donnée légitime peut-elle échouer à cette contrainte ?

      Oui -> Warning. Bloquer rejetterait du vrai.
      Non -> continuer au test 3.

      ISO 45001 §5.4, la consultation des travailleurs, ne se rattache
      à aucun danger unique. C'est une exigence de système de gestion.
      La rendre obligatoire rejetterait une exigence parfaitement valide.

  TEST 3 — Si on bloque, l'équipe d'ingestion contournera-t-elle ?

      Oui -> Warning. Une contrainte contournée est pire qu'aucune
             contrainte : elle remplit le graphe de fabrications qui
             ont l'air autorisées.
      Non -> Violation.

      C'est le test que les modélisateurs oublient. Une barrière dure
      sur un champ difficile à remplir ne produit pas de la qualité,
      elle produit du remplissage bidon.

LA RÈGLE À RETENIR
------------------
    Barrière dure  là où la mauvaise donnée produit une réponse
                   fausse et assurée.
    Signal doux    là où la donnée est incomplète mais honnête.
"""

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    VIOLATION = "sh:Violation"
    WARNING = "sh:Warning"
    INFO = "sh:Info"


@dataclass
class SeverityDecision:
    """Une décision de sévérité, avec sa justification.

    On garde la justification parce qu'un choix de sévérité non justifié
    est indéfendable en revue. Elle est écrite en commentaire dans le
    fichier SHACL généré : la prochaine personne qui lit la shape voit
    le raisonnement, pas seulement le verdict.
    """
    severity: Severity
    rationale: str
    failed_test: str


def decide_severity(
    *,
    produces_wrong_answer: bool,
    legitimate_data_can_fail: bool,
    likely_to_be_gamed: bool,
    field_name: str = "",
) -> SeverityDecision:
    """Applique les trois tests, dans l'ordre.

    L'ordre compte. Le test 1 tranche seul : si le défaut produit une
    réponse fausse, aucune considération pratique ne justifie de laisser
    passer. Les tests 2 et 3 ne s'appliquent qu'aux défauts qui rendent
    la donnée incomplète.
    """

    # TEST 1 — fausseté. Décisif, et sans appel.
    if produces_wrong_answer:
        return SeverityDecision(
            severity=Severity.VIOLATION,
            rationale=(
                f"Sans '{field_name}', la donnée produit une réponse fausse, "
                "pas seulement incomplète. Le coût d'une réponse de conformité "
                "erronée dépasse toujours le coût d'un blocage d'ingestion."
            ),
            failed_test="TEST 1 : produit une réponse fausse",
        )

    # TEST 2 — faux positifs sur de la donnée réelle.
    if legitimate_data_can_fail:
        return SeverityDecision(
            severity=Severity.WARNING,
            rationale=(
                f"De la donnée légitime peut ne pas avoir de '{field_name}'. "
                "Bloquer rejetterait du vrai. On tolère et on suit le trou "
                "comme métrique de couverture."
            ),
            failed_test="TEST 2 : de la donnée légitime échouerait",
        )

    # TEST 3 — contournement.
    if likely_to_be_gamed:
        return SeverityDecision(
            severity=Severity.WARNING,
            rationale=(
                f"'{field_name}' est coûteux à remplir correctement. Une "
                "barrière dure produirait du remplissage bidon plutôt que de "
                "la qualité. Une contrainte contournée est pire qu'aucune "
                "contrainte."
            ),
            failed_test="TEST 3 : serait contournée",
        )

    return SeverityDecision(
        severity=Severity.VIOLATION,
        rationale=(
            f"'{field_name}' est obligatoire, remplissable, et son absence "
            "rend la donnée inexploitable. Barrière dure justifiée."
        ),
        failed_test="Aucun test échoué : blocage sûr",
    )


# ---------------------------------------------------------------------
# Heuristiques par défaut
#
# Le générateur doit pouvoir proposer une sévérité quand l'auteur du
# spec ne l'a pas déclarée. Ces heuristiques encodent ce qu'on a appris
# en modélisant le domaine SST.
#
# Ce sont des PROPOSITIONS, pas des verdicts : le spec peut toujours
# les écraser. Un générateur qui impose ses choix à l'expert du domaine
# ne sera pas utilisé.
# ---------------------------------------------------------------------

#: Champs dont l'absence produit une réponse fausse, pas incomplète.
FIELDS_PRODUCING_WRONG_ANSWERS = {
    "citation",       # réponse de conformité invérifiable
    "scopedTo",       # concept sans régime : aucun sens légal
    "statedIn",       # exigence sans source
    "validFrom",      # impossible de savoir si la règle s'applique
    "recordedAt",     # impossible de répondre « que savions-nous le X »
    "basis",          # affirmation inter-régimes non auditable
    "wasAttributedTo",  # aucune provenance, aucune responsabilité
    "confidence",     # équivalence affirmée sans mesure d'incertitude
}

#: Champs qu'une source réelle laisse souvent vides, sans que la donnée
#: soit fautive.
#:
#: NOTE DE PORTAGE — à lire avant d'ajouter un domaine.
#: Cet ensemble était d'abord peuplé du seul vocabulaire de la
#: conformité SST. En générant le domaine supply chain, tous les champs
#: sont sortis en barrière dure : 21 violations, 0 avertissement. Le
#: ratio était le signal. Le générateur n'avait pas tort sur le fond —
#: il ne connaissait simplement pas les noms du nouveau domaine.
#:
#: C'est la limite honnête de l'approche : les heuristiques par NOM de
#: champ ne se portent pas d'un domaine à l'autre. Un générateur mûr
#: déclarerait ces catégories dans le spec plutôt que dans le code.
FIELDS_WITH_LEGITIMATE_GAPS = {
    # Conformité réglementaire
    "addressesHazard",   # les exigences de système ne visent aucun danger
    "supersedes",        # une première version ne remplace rien
    "validTo",           # une règle en vigueur n'a pas de date de fin
    "appliesToSector",   # beaucoup d'obligations sont transversales

    # Chaîne d'approvisionnement
    "appliesToConcept",  # beaucoup de règles de planif sont transversales
    "champTechnique",    # inconnu tant que le concept n'est pas câblé
    "proprietaire",      # souvent vide au moment de l'inventaire

    # Applications de l'IA en SST
    "viseGenreAccident",  # toutes les applications ne ciblent pas un
                          # événement codé : un modèle d'exposition
                          # chimique vise un danger, pas un accident
    "lexiconRef",         # rattachement au lexique fait après coup
    "rangHierarchie",     # les activités de surveillance ne se situent
                          # pas dans la hiérarchie des contrôles
}

#: Champs coûteux à remplir correctement, donc candidats au remplissage
#: bidon si on les rend obligatoires.
FIELDS_LIKELY_GAMED = {
    "reviewedBy",
    "riskScore",
    "estimatedCost",
}


def propose_severity(field_name: str) -> SeverityDecision:
    """Propose une sévérité à partir du seul nom du champ."""
    return decide_severity(
        produces_wrong_answer=field_name in FIELDS_PRODUCING_WRONG_ANSWERS,
        legitimate_data_can_fail=field_name in FIELDS_WITH_LEGITIMATE_GAPS,
        likely_to_be_gamed=field_name in FIELDS_LIKELY_GAMED,
        field_name=field_name,
    )
