from django.core.exceptions import ValidationError
from apps.core.choices import StatutService


def validate_resource(obj):
    obj.full_clean()
    # UNAVAILABLE/REVIEW_NEEDED peuvent être publiés comme information de repli,
    # mais jamais comme contact utilisable ou service confirmé.
    if (
        obj.statut_service != StatutService.ACTIVE
        and obj.kind != "INTERNAL"
        and not obj.ressource_repli_id
    ):
        raise ValidationError(f"{obj.cle}: service non actif sans ressource de repli")
    seen = set()
    cur = obj
    while cur is not None:
        if cur.pk in seen:
            raise ValidationError(f"{obj.cle}: cycle de ressources de repli")
        seen.add(cur.pk)
        cur = cur.ressource_repli
    return True
