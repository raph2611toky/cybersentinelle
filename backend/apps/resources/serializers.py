from rest_framework import serializers
from apps.content_api.serializers import bilingual
from apps.core.serializers import ValidatedModelSerializer, RelationSummarySerializer
from .models import Source, RessourceAide
from apps.translation.mixins import FrenchFirstMixin,french_only_fields


def resource_dict(obj):
    result = {
        "id": obj.cle,
        "title": bilingual(obj, "titre"),
        "description": bilingual(obj, "description"),
        "action": bilingual(obj, "action"),
        "audience": bilingual(obj, "audience"),
        "kind": obj.kind.lower(),
        "href": (obj.href or None) if obj.statut_service == "ACTIVE" else None,
        "source": bilingual(obj.source, "nom"),
        "sourceUrl": obj.source.url_officielle or None,
        "verifiedAt": obj.verifie_le.isoformat() if obj.verifie_le else None,
        "reviewerRole": obj.verificateur_role or None,
        "status": obj.statut_service.lower(),
    }
    return result


class ResourceSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.DictField(child=serializers.CharField())
    description = serializers.DictField(child=serializers.CharField())
    action = serializers.DictField(child=serializers.CharField())
    audience = serializers.DictField(child=serializers.CharField())
    kind = serializers.ChoiceField(choices=["call", "external", "internal"])
    href = serializers.CharField(allow_null=True)
    source = serializers.DictField(child=serializers.CharField())
    sourceUrl = serializers.CharField(allow_null=True)
    verifiedAt = serializers.DateField(allow_null=True)
    reviewerRole = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=["active", "unavailable", "review_needed"])


class SourceEditorSerializer(FrenchFirstMixin, ValidatedModelSerializer):
    translation_fields = ('nom', 'portee')
    translation_state = FrenchFirstMixin.translation_state
    class Meta:
        model = Source
        extra_kwargs = french_only_fields(('nom', 'portee'))
        fields = (
            "id",
            "created_at",
            "updated_at",
            "translation_state",
            "code",
            "nom_fr",
            "nom_mg",
            "type",
            "url_officielle",
            "portee_fr",
            "portee_mg",
            "dernier_controle_le",
            "actif",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class RessourceAideEditorSerializer(FrenchFirstMixin, ValidatedModelSerializer):
    translation_fields = ('titre', 'description', 'action', 'audience', 'limites', 'zone')
    translation_state = FrenchFirstMixin.translation_state
    source_detail = RelationSummarySerializer(
        source="source", read_only=True, allow_null=True
    )
    ressource_repli_detail = RelationSummarySerializer(
        source="ressource_repli", read_only=True, allow_null=True
    )

    class Meta:
        model = RessourceAide
        extra_kwargs = french_only_fields(('titre', 'description', 'action', 'audience', 'limites', 'zone'))
        fields = (
            "id",
            "created_at",
            "updated_at",
            "translation_state",
            "revision",
            "statut_editorial",
            "valide_le",
            "validateur_role",
            "relecture_fr_le",
            "relecture_mg_le",
            "relecteur_fr_role",
            "relecteur_mg_role",
            "note_validation",
            "publie_le",
            "cle",
            "titre_fr",
            "titre_mg",
            "description_fr",
            "description_mg",
            "action_fr",
            "action_mg",
            "audience_fr",
            "audience_mg",
            "limites_fr",
            "limites_mg",
            "zone_fr",
            "zone_mg",
            "pour_mineurs",
            "kind",
            "href",
            "source",
            "verifie_le",
            "verificateur_role",
            "statut_service",
            "ressource_repli",
            "ordre",
            "source_detail",
            "ressource_repli_detail",
        )
        read_only_fields = ("id", "created_at", "updated_at", "publie_le")
