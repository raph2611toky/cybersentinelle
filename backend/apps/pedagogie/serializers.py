from rest_framework import serializers
from apps.content_api.serializers import bilingual
from apps.core.serializers import ValidatedModelSerializer, RelationSummarySerializer
from .models import QuestionPedagogique


def question_dict(obj):
    return {
        "id": obj.cle,
        "topic": obj.sujet.code,
        "question": bilingual(obj, "question"),
        "answer": bilingual(obj, "reponse"),
        "reviewStatus": "approved",
        "version": obj.revision,
    }


class QuestionSerializer(serializers.Serializer):
    id = serializers.CharField()
    topic = serializers.CharField()
    question = serializers.DictField(child=serializers.CharField())
    answer = serializers.DictField(child=serializers.CharField())
    reviewStatus = serializers.ChoiceField(choices=["approved"])
    version = serializers.CharField()


class QuestionPedagogiqueEditorSerializer(ValidatedModelSerializer):
    sujet_detail = RelationSummarySerializer(
        source="sujet", read_only=True, allow_null=True
    )
    ressources_liees_details = RelationSummarySerializer(
        source="ressources_liees", many=True, read_only=True
    )

    class Meta:
        model = QuestionPedagogique
        fields = (
            "id",
            "created_at",
            "updated_at",
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
            "sujet",
            "question_fr",
            "question_mg",
            "reponse_fr",
            "reponse_mg",
            "ressources_liees",
            "ordre",
            "sujet_detail",
            "ressources_liees_details",
        )
        read_only_fields = ("id", "created_at", "updated_at", "publie_le")
