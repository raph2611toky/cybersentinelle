import copy
from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework import serializers
from .models import Langue


class ValidatedModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        candidate = copy.copy(self.instance) if self.instance else self.Meta.model()
        excluded = []
        for field in candidate._meta.many_to_many:
            excluded.append(field.name)
        for name, value in attrs.items():
            if name not in excluded:
                setattr(candidate, name, value)
        if isinstance(candidate, Langue):
            candidate.default_slot = 1 if candidate.par_defaut else None
        try:
            candidate.full_clean(exclude=excluded)
        except ModelValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"non_field_errors": exc.messages}
            ) from exc
        return attrs


class LangueEditorSerializer(ValidatedModelSerializer):
    class Meta:
        model = Langue
        fields = (
            "id",
            "code",
            "nom_fr",
            "nom_mg",
            "nom_natif",
            "par_defaut",
            "actif",
            "ordre",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class SessionSerializer(serializers.Serializer):
    active = serializers.BooleanField(read_only=True)
    language = serializers.ChoiceField(choices=["fr", "mg"], required=False)
    expires_at = serializers.DateTimeField(read_only=True)
    elapsed_seconds = serializers.IntegerField(read_only=True)


class RelationSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    label = serializers.CharField(source="__str__", read_only=True)
