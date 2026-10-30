import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.content_api.models import Tantara, Noeud, OptionDecision
from apps.content_api.validation import validate_story_graph


@pytest.mark.django_db
def test_two_decisions_graph_success():
    t = Tantara.objects.create(
        slug="tsy-irery",
        numero="02",
        decisions_attendues=2,
        duree="10 min",
        palette="violet",
        titre_fr="A",
        titre_mg="A",
        sous_titre_fr="B",
        sous_titre_mg="B",
        theme_fr="C",
        theme_mg="C",
        description_fr="D",
        description_mg="D",
        avertissement_fr="E",
        avertissement_mg="E",
    )
    end = Noeud.objects.create(
        tantara=t,
        cle="end",
        type="ENDING",
        titre_fr="F",
        titre_mg="F",
        texte_fr="X",
        texte_mg="X",
    )
    d2 = Noeud.objects.create(
        tantara=t,
        cle="d2",
        type="DECISION",
        poids=10,
        titre_fr="Q2",
        titre_mg="Q2",
        texte_fr="T2",
        texte_mg="T2",
    )
    start = Noeud.objects.create(
        tantara=t,
        cle="start",
        type="DECISION",
        poids=10,
        titre_fr="Q1",
        titre_mg="Q1",
        texte_fr="T1",
        texte_mg="T1",
    )
    for n, target in [(start, d2), (d2, end)]:
        for idx in range(2):
            OptionDecision.objects.create(
                noeud=n,
                cle=f"opt{idx}",
                label_fr="A",
                label_mg="A",
                feedback_fr="B",
                feedback_mg="B",
                qualite=Decimal("0.500"),
                noeud_cible=target,
                ordre=idx,
            )
    assert validate_story_graph(t)
    OptionDecision.objects.filter(noeud=d2).first().delete()
    with pytest.raises(ValidationError):
        validate_story_graph(t)
