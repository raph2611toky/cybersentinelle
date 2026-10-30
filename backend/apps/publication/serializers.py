from rest_framework import serializers
from .models import VersionContenu, FichierContenu


class FileManifestSerializer(serializers.Serializer):
    path = serializers.CharField()
    type = serializers.ChoiceField(choices=["STORY", "QUESTIONS", "RESOURCES"])
    sha256 = serializers.CharField()
    bytes = serializers.IntegerField(min_value=0)
    language = serializers.CharField(allow_null=True)


class ContentVersionSerializer(serializers.Serializer):
    version = serializers.CharField()
    date = serializers.DateTimeField()
    languages = serializers.ListField(child=serializers.CharField())
    sha256 = serializers.CharField()
    files = FileManifestSerializer(many=True)


class ReleaseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FichierContenu
        fields = ("id", "chemin", "type", "sha256", "taille_octets")
        read_only_fields = fields


class ReleaseEditorSerializer(serializers.ModelSerializer):
    fichiers = ReleaseFileSerializer(many=True, read_only=True)

    class Meta:
        model = VersionContenu
        fields = (
            "id",
            "numero",
            "statut",
            "date_publication",
            "digest_global",
            "journal",
            "fichiers",
            "created_at",
        )
        read_only_fields = fields


class PublishSerializer(serializers.Serializer):
    numero = serializers.RegexField(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$", max_length=40)
    journal = serializers.CharField(required=False, allow_blank=True, max_length=2000)
