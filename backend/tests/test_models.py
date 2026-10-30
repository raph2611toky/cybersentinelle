import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from apps.core.models import Langue
from apps.core.validators import relative_asset
from apps.publication.models import VersionContenu


@pytest.mark.django_db
def test_portable_default_uniqueness():
    Langue.objects.create(
        code="fr",
        nom_fr="Français",
        nom_mg="Frantsay",
        nom_natif="Français",
        par_defaut=True,
    )
    with pytest.raises(IntegrityError):
        Langue.objects.create(
            code="mg",
            nom_fr="Malgache",
            nom_mg="Malagasy",
            nom_natif="Malagasy",
            par_defaut=True,
        )


@pytest.mark.django_db
def test_portable_active_slot_uniqueness():
    VersionContenu.objects.create(numero="v1", statut="ACTIVE")
    with pytest.raises(IntegrityError):
        VersionContenu.objects.create(numero="v2", statut="ACTIVE")


def test_relative_path_rejects_traversal():
    with pytest.raises(ValidationError):
        relative_asset("../etc/passwd")
    with pytest.raises(ValidationError):
        relative_asset("/etc/passwd")
