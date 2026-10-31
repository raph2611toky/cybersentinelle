"""Tests des données de référence créées automatiquement au déploiement."""
import pytest
from django.core.management import call_command

from apps.core.models import Langue
from apps.content_api.models import Sujet
from apps.resources.models import Source


@pytest.mark.django_db
def test_seed_defaults_creates_references_and_is_idempotent():
    call_command("seed_defaults")
    assert set(Langue.objects.values_list("code", flat=True)) == {"fr", "mg"}
    assert Langue.objects.filter(code="fr", par_defaut=True, actif=True).exists()
    assert Sujet.objects.count() == 6
    assert Source.objects.filter(
        code="referentiel-safidiko", type="REFERENTIEL_INTERNE"
    ).exists()

    fr = Langue.objects.get(code="fr")
    fr.nom_fr = "Français personnalisé"
    fr.save(update_fields=["nom_fr"])
    original_ids = set(Langue.objects.values_list("id", flat=True))
    call_command("seed_defaults")
    assert Langue.objects.get(code="fr").nom_fr == "Français personnalisé"
    assert set(Langue.objects.values_list("id", flat=True)) == original_ids
    assert Sujet.objects.count() == 6
    assert Source.objects.count() == 1


@pytest.mark.django_db
def test_seed_defaults_preserves_existing_default_and_inactive_subject():
    mg = Langue.objects.create(
        code="mg", nom_fr="Malgache", nom_mg="Malagasy",
        nom_natif="Malagasy", par_defaut=True, actif=True,
    )
    Sujet.objects.create(
        code="rumeurs", libelle_fr="Déjà édité", libelle_mg="Efa novaina", actif=False
    )
    call_command("seed_defaults")
    mg.refresh_from_db()
    assert mg.par_defaut is True
    assert Langue.objects.get(code="fr").par_defaut is False
    topic = Sujet.objects.get(code="rumeurs")
    assert topic.libelle_fr == "Déjà édité"
    assert topic.actif is False
