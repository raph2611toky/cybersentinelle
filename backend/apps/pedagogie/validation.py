from django.core.exceptions import ValidationError
from apps.core.choices import StatutEditorial


def validate_question(obj):
    obj.full_clean()
    if obj.statut_editorial not in {StatutEditorial.APPROUVE, StatutEditorial.PUBLIE}:
        raise ValidationError(f"{obj.cle}: question non approuvée")
    if not obj.sujet.actif:
        raise ValidationError(f"{obj.cle}: sujet inactif")
    return True
