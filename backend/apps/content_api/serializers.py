"""Contrat V14, UUIDs et champs privés jamais exposés."""

from helpers.helper import media_url
from rest_framework import serializers
from .models import Tantara, Noeud, OptionDecision
from apps.core.serializers import ValidatedModelSerializer, RelationSummarySerializer
from .models import Sujet, Visuel, Tantara, Noeud, OptionDecision


def bilingual(obj, attr):
    return {"fr": getattr(obj, attr + "_fr"), "mg": getattr(obj, attr + "_mg")}


def absolute_static_url(request, visual):
    if not visual or not visual.actif:
        return None
    return media_url(visual.fichier.name or visual.chemin_asset, request)


def option_dict(o):
    return {
        "id": o.cle,
        "label": bilingual(o, "label"),
        "feedback": bilingual(o, "feedback"),
        "quality": float(o.qualite),
        "next": o.noeud_cible.cle,
    }


def node_dict(n, request):
    data = {
        "kind": n.type.lower(),
        "title": bilingual(n, "titre"),
        "text": bilingual(n, "texte"),
    }
    if n.type == "SCENE":
        data.update(
            {
                "tag": n.tag,
                "visual": n.visuel.code if n.visuel else "",
                "next": n.noeud_suivant.cle,
            }
        )
        if n.visuel and request:
            data["visual_url"] = absolute_static_url(request, n.visuel)
    elif n.type == "DECISION":
        data["weight"] = n.poids
        data["options"] = [option_dict(o) for o in n.options.all()]
    return data


def story_dict(s, request, include_nodes=False):
    data = {
        "id": s.slug,
        "number": s.numero,
        "title": bilingual(s, "titre"),
        "subtitle": bilingual(s, "sous_titre"),
        "theme": bilingual(s, "theme"),
        "description": bilingual(s, "description"),
        "warning": bilingual(s, "avertissement"),
        "duration": s.duree,
        "expectedDecisions": s.decisions_attendues,
        "palette": s.palette,
        "heroVisual": s.visuel_heros.code if s.visuel_heros else "",
    }
    if s.visuel_heros and request:
        data["heroVisual_url"] = absolute_static_url(request, s.visuel_heros)
    if include_nodes:
        data["nodes"] = {n.cle: node_dict(n, request) for n in s.noeuds.all()}
    return data


class StoryListSerializer(serializers.Serializer):
    id = serializers.CharField()
    number = serializers.CharField()
    title = serializers.DictField(child=serializers.CharField())
    subtitle = serializers.DictField(child=serializers.CharField())
    theme = serializers.DictField(child=serializers.CharField())
    description = serializers.DictField(child=serializers.CharField())
    warning = serializers.DictField(child=serializers.CharField())
    duration = serializers.CharField()
    expectedDecisions = serializers.IntegerField()
    palette = serializers.CharField()
    heroVisual = serializers.CharField()
    heroVisual_url = serializers.URLField(required=False)


class StoryDetailSerializer(StoryListSerializer):
    nodes = serializers.DictField(child=serializers.JSONField())


class SujetEditorSerializer(ValidatedModelSerializer):
    class Meta:
        model = Sujet
        fields = (
            "id",
            "created_at",
            "updated_at",
            "code",
            "libelle_fr",
            "libelle_mg",
            "description_fr",
            "description_mg",
            "ordre",
            "actif",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class VisuelEditorSerializer(ValidatedModelSerializer):
    fichier_url = serializers.SerializerMethodField()
    chemin_asset_url = serializers.SerializerMethodField()

    def get_fichier_url(self, obj):
        request = self.context.get("request")
        if not obj.fichier:
            return None
        url = obj.fichier.url
        return request.build_absolute_uri(url) if request else url

    def get_chemin_asset_url(self, obj):
        if not obj.chemin_asset:
            return None
        return media_url(obj.chemin_asset, self.context.get("request"))

    def validate_fichier(self, value):
        from helpers.helper import normalize_image
        from django.core.exceptions import ValidationError

        try:
            return normalize_image(value)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate(self, attrs):
        import hashlib

        upload = attrs.get("fichier")
        if upload:
            attrs["format"] = "PNG"
            attrs["largeur_px"], attrs["hauteur_px"] = upload.image_dimensions
            attrs["sha256"] = hashlib.sha256(upload.read()).hexdigest()
            upload.seek(0)
        return super().validate(attrs)

    class Meta:
        model = Visuel
        fields = (
            "id",
            "created_at",
            "updated_at",
            "code",
            "type",
            "fichier",
            "fichier_url",
            "chemin_asset",
            "chemin_asset_url",
            "format",
            "largeur_px",
            "hauteur_px",
            "alt_fr",
            "alt_mg",
            "decoratif",
            "licence",
            "url_provenance",
            "attribution",
            "sha256",
            "actif",
        )
        read_only_fields = ("id", "created_at", "updated_at", "fichier_url", "chemin_asset_url")


class TantaraEditorSerializer(ValidatedModelSerializer):
    visuel_heros_url = serializers.SerializerMethodField()

    def get_visuel_heros_url(self, obj):
        return absolute_static_url(self.context.get('request'), obj.visuel_heros) if self.context.get('request') else None

    visuel_heros_detail = RelationSummarySerializer(
        source="visuel_heros", read_only=True, allow_null=True
    )
    sujets_details = RelationSummarySerializer(
        source="sujets", many=True, read_only=True
    )

    class Meta:
        model = Tantara
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
            "slug",
            "numero",
            "titre_fr",
            "titre_mg",
            "sous_titre_fr",
            "sous_titre_mg",
            "theme_fr",
            "theme_mg",
            "description_fr",
            "description_mg",
            "avertissement_fr",
            "avertissement_mg",
            "duree",
            "decisions_attendues",
            "palette",
            "visuel_heros",
            "sujets",
            "ordre",
            "visuel_heros_url",
            "visuel_heros_detail",
            "sujets_details",
        )
        read_only_fields = ("id", "created_at", "updated_at", "publie_le")


class NoeudEditorSerializer(ValidatedModelSerializer):
    visuel_url = serializers.SerializerMethodField()

    def get_visuel_url(self, obj):
        return absolute_static_url(self.context.get('request'), obj.visuel) if self.context.get('request') else None

    tantara_detail = RelationSummarySerializer(
        source="tantara", read_only=True, allow_null=True
    )
    visuel_detail = RelationSummarySerializer(
        source="visuel", read_only=True, allow_null=True
    )
    noeud_suivant_detail = RelationSummarySerializer(
        source="noeud_suivant", read_only=True, allow_null=True
    )

    class Meta:
        model = Noeud
        fields = (
            "id",
            "created_at",
            "updated_at",
            "tantara",
            "cle",
            "type",
            "titre_fr",
            "titre_mg",
            "texte_fr",
            "texte_mg",
            "tag",
            "visuel",
            "poids",
            "noeud_suivant",
            "ordre",
            "tantara_detail",
            "visuel_url",
            "visuel_detail",
            "noeud_suivant_detail",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class OptionDecisionEditorSerializer(ValidatedModelSerializer):
    noeud_detail = RelationSummarySerializer(
        source="noeud", read_only=True, allow_null=True
    )
    noeud_cible_detail = RelationSummarySerializer(
        source="noeud_cible", read_only=True, allow_null=True
    )

    class Meta:
        model = OptionDecision
        fields = (
            "id",
            "created_at",
            "updated_at",
            "noeud",
            "cle",
            "label_fr",
            "label_mg",
            "feedback_fr",
            "feedback_mg",
            "qualite",
            "noeud_cible",
            "ordre",
            "noeud_detail",
            "noeud_cible_detail",
        )
        read_only_fields = ("id", "created_at", "updated_at")
