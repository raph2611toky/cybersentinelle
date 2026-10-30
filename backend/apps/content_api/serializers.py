"""Contrat V14, UUIDs et champs privés jamais exposés."""

from helpers.helper import media_url
from rest_framework import serializers
from .models import Tantara, Noeud, OptionDecision
from apps.core.serializers import ValidatedModelSerializer, RelationSummarySerializer
from .models import Sujet, Visuel, Tantara, Noeud, OptionDecision
from apps.translation.mixins import FrenchFirstMixin, french_only_fields


def bilingual(obj, attr):
    return {"fr": getattr(obj, attr + "_fr"), "mg": getattr(obj, attr + "_mg")}


def absolute_static_url(request, visual):
    if not visual or not visual.actif:
        return None
    if visual.fichier:
        url = visual.fichier.url
        return request.build_absolute_uri(url) if request else url
    return media_url(visual.chemin_asset, request)


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
        "cover": f"covers/{s.slug}.png" if s.image_cover else "",
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
    cover = serializers.CharField(required=False, allow_blank=True)
    cover_url = serializers.URLField(required=False)
    heroVisual_url = serializers.URLField(required=False)


class StoryDetailSerializer(StoryListSerializer):
    nodes = serializers.DictField(child=serializers.JSONField())


class SujetEditorSerializer(FrenchFirstMixin, ValidatedModelSerializer):
    translation_fields = ('libelle', 'description')
    translation_state = FrenchFirstMixin.translation_state
    class Meta:
        model = Sujet
        extra_kwargs = french_only_fields(('libelle', 'description'))
        fields = (
            "id",
            "created_at",
            "updated_at",
            "translation_state",
            "code",
            "libelle_fr",
            "libelle_mg",
            "description_fr",
            "description_mg",
            "ordre",
            "actif",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class VisuelEditorSerializer(FrenchFirstMixin,ValidatedModelSerializer):
    translation_fields=("alt",)
    translation_state=FrenchFirstMixin.translation_state
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
        extra_kwargs = french_only_fields(("alt",))
        fields = (
            "id",
            "created_at",
            "updated_at",
            "translation_state",
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


class TantaraEditorSerializer(FrenchFirstMixin, ValidatedModelSerializer):
    image_cover_url = serializers.SerializerMethodField(read_only=True)
    effacer_couverture = serializers.BooleanField(write_only=True, required=False, default=False)

    def get_image_cover_url(self, obj):
        if not obj.image_cover:
            return None
        url = obj.image_cover.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def validate_image_cover(self, upload):
        if upload is None:
            return None
        from helpers.helper import normalize_image
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            clean = normalize_image(upload)  # PNG réencodé, sans métadonnées d'origine.
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        if clean.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image réencodée limitée à 5 Mo.")
        return clean

    def validate(self, attrs):
        clear = attrs.pop("effacer_couverture", False)
        if clear and attrs.get("image_cover") is not None:
            raise serializers.ValidationError({"image_cover": "Ne pas envoyer une image et demander son retrait simultanément."})
        if clear:
            attrs["image_cover"] = None
        return super().validate(attrs)

    def validate_duree(self, value):
        import re
        match = re.fullmatch(r'([1-9][0-9]{0,2}) min', value.strip())
        if not match or not (1 <= int(match.group(1)) <= 180):
            raise serializers.ValidationError('Durée attendue : 1 à 180 min (ex. 5 min).')
        return f"{int(match.group(1))} min"

    translation_fields = ('titre', 'sous_titre', 'theme', 'description', 'avertissement')
    translation_state = FrenchFirstMixin.translation_state
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
        extra_kwargs = french_only_fields(('titre', 'sous_titre', 'theme', 'description', 'avertissement'))
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
            "image_cover",
            "image_cover_url",
            "effacer_couverture",
            "decisions_attendues",
            "palette",
            "visuel_heros",
            "sujets",
            "ordre",
            "visuel_heros_url",
            "visuel_heros_detail",
            "sujets_details",
        )
        read_only_fields = ("id", "created_at", "updated_at", "publie_le", "image_cover_url")


class NoeudEditorSerializer(FrenchFirstMixin, ValidatedModelSerializer):
    translation_fields = ('titre', 'texte')
    translation_state = FrenchFirstMixin.translation_state
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
        extra_kwargs = french_only_fields(('titre', 'texte'))
        fields = (
            "id",
            "created_at",
            "updated_at",
            "translation_state",
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


class OptionDecisionEditorSerializer(FrenchFirstMixin, ValidatedModelSerializer):
    translation_fields = ('label', 'feedback')
    translation_state = FrenchFirstMixin.translation_state
    noeud_detail = RelationSummarySerializer(
        source="noeud", read_only=True, allow_null=True
    )
    noeud_cible_detail = RelationSummarySerializer(
        source="noeud_cible", read_only=True, allow_null=True
    )

    class Meta:
        model = OptionDecision
        extra_kwargs = french_only_fields(('label', 'feedback'))
        fields = (
            "id",
            "created_at",
            "updated_at",
            "translation_state",
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
