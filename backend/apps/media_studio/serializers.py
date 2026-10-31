"""Serializers d'édition : IDs internes conservés uniquement côté staff."""
from django.urls import reverse
from rest_framework import serializers
from apps.core.serializers import ValidatedModelSerializer
from .models import MediaAsset, VoiceProfile, SceneMedia, DialogueLine, GenerationJob


class MediaAssetSerializer(serializers.ModelSerializer):
    fichier_url = serializers.SerializerMethodField()
    langue = serializers.SlugRelatedField(slug_field='code', read_only=True)

    class Meta:
        model = MediaAsset
        fields = ('id', 'titre', 'type', 'mime_type', 'taille_octets', 'duree_ms', 'largeur_px', 'hauteur_px',
                  'sha256', 'origine', 'provider', 'langue', 'licence', 'droits_confirmes', 'fichier_url', 'created_at')
        read_only_fields = fields

    def get_fichier_url(self, obj):
        request = self.context.get('request')
        path = reverse('studio-media-download', kwargs={'pk': obj.pk})
        return request.build_absolute_uri(path) if request else path


class VoiceSerializer(ValidatedModelSerializer):
    class Meta:
        model = VoiceProfile
        fields = ('id', 'nom', 'langue', 'provider', 'model_id', 'voice_id', 'style', 'actif', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class SceneSerializer(ValidatedModelSerializer):
    video_finale_url = serializers.SerializerMethodField()
    audio_finale_url = serializers.SerializerMethodField()
    audio_source_url = serializers.SerializerMethodField()
    video_source_url = serializers.SerializerMethodField()
    image_source_url = serializers.SerializerMethodField()
    audio_embedded = serializers.SerializerMethodField()

    class Meta:
        model = SceneMedia
        fields = ('id', 'noeud', 'langue', 'mode', 'image', 'video', 'audio', 'sous_titres',
                  'video_finale', 'video_finale_url', 'audio_finale', 'audio_finale_url',
                  'video_source_url', 'image_source_url', 'audio_source_url', 'audio_embedded',
                  'sync_mode', 'audio_trim_start_ms', 'audio_trim_end_ms', 'narration_texte', 'voix', 'statut', 'created_at', 'updated_at')
        read_only_fields = ('id', 'video_finale', 'video_finale_url', 'audio_finale', 'audio_finale_url', 'video_source_url', 'image_source_url', 'audio_source_url', 'audio_embedded', 'statut', 'created_at', 'updated_at')

    def get_video_finale_url(self, obj):
        request = self.context.get('request')
        if not obj.video_finale_id:
            return None
        path = reverse('studio-media-download', kwargs={'pk': obj.video_finale_id})
        return request.build_absolute_uri(path) if request else path

    def get_audio_finale_url(self, obj):
        if not obj.audio_finale_id:
            return None
        request = self.context.get('request')
        path = reverse('studio-media-download', kwargs={'pk': obj.audio_finale_id})
        return request.build_absolute_uri(path) if request else path

    def _asset_url(self, asset_id):
        if not asset_id:
            return None
        path = reverse('studio-media-download', kwargs={'pk': asset_id})
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path

    def get_audio_source_url(self, obj):
        return self._asset_url(obj.audio_id)

    def get_video_source_url(self, obj):
        return self._asset_url(obj.video_id)

    def get_image_source_url(self, obj):
        return self._asset_url(obj.image_id)

    def get_audio_embedded(self, obj):
        # Le fichier final FFmpeg contient la narration AAC, pas un second lecteur.
        return bool(obj.video_finale_id and obj.statut == SceneMedia.Status.READY
                    and obj.mode in {SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.IMAGE_AUDIO})

    def validate(self, attrs):
        # Les scènes ET les fins peuvent avoir une vidéo, jamais les décisions.
        node = attrs.get('noeud', getattr(self.instance, 'noeud', None))
        if node is not None and node.type not in ('SCENE', 'ENDING'):
            raise serializers.ValidationError({'noeud': 'Les médias sont réservés aux scènes et aux fins.'})
        if self.instance is not None and 'noeud' in attrs and attrs['noeud'].pk != self.instance.noeud_id:
            raise serializers.ValidationError({'noeud': 'Le nœud ne peut pas être modifié : créez un autre montage.'})
        # Interdire les associations invalides avant l'enregistrement.
        mode = attrs.get('mode', getattr(self.instance, 'mode', SceneMedia.Mode.TEXT_ONLY))
        if mode == SceneMedia.Mode.AUDIO_ONLY:
            if attrs.get('video') or attrs.get('image'):
                raise serializers.ValidationError({'mode': 'Audio seul : aucune image ou vidéo ne doit être associée.'})
        start = attrs.get('audio_trim_start_ms', getattr(self.instance, 'audio_trim_start_ms', 0))
        end = attrs.get('audio_trim_end_ms', getattr(self.instance, 'audio_trim_end_ms', None))
        if end is not None and end <= start:
            raise serializers.ValidationError({'audio_trim_end_ms': 'La fin doit être après le début.'})
        attrs['statut'] = SceneMedia.Status.DRAFT
        return super().validate(attrs)


class DialogueSerializer(ValidatedModelSerializer):
    class Meta:
        model = DialogueLine
        fields = ('id', 'scene', 'ordre', 'personnage', 'texte', 'voix', 'audio', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class JobSerializer(serializers.ModelSerializer):
    resultat_url = serializers.SerializerMethodField()
    class Meta:
        model = GenerationJob
        fields = ('id', 'type', 'statut', 'scene', 'dialogue', 'voix', 'resultat', 'resultat_url', 'code_erreur', 'debut_le', 'fin_le', 'created_at')
        read_only_fields = fields

    def get_resultat_url(self, obj):
        if not obj.resultat_id:
            return None
        path = reverse('studio-media-download', kwargs={'pk': obj.resultat_id})
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path


class MediaUploadInput(serializers.Serializer):
    titre = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=MediaAsset.Kind.choices)
    licence = serializers.CharField(max_length=160)
    droits_confirmes = serializers.BooleanField()
    langue = serializers.CharField(max_length=2, required=False, allow_blank=True)
    fichier = serializers.FileField()


class MediaMetadataInput(serializers.Serializer):
    """Edition des seules métadonnées : le fichier, son type et son hash restent immuables."""
    titre = serializers.CharField(max_length=200, required=False, allow_blank=False, trim_whitespace=True)
    licence = serializers.CharField(max_length=160, required=False, allow_blank=False, trim_whitespace=True)
    langue = serializers.CharField(max_length=2, required=False, allow_blank=True)


class TTSInput(serializers.Serializer):
    scene = serializers.PrimaryKeyRelatedField(queryset=SceneMedia.objects.all())
    voix = serializers.PrimaryKeyRelatedField(queryset=VoiceProfile.objects.filter(actif=True))
    texte = serializers.CharField(max_length=2500, trim_whitespace=True, allow_blank=False)

    def validate(self, attrs):
        from django.conf import settings
        if attrs['scene'].langue_id != attrs['voix'].langue_id:
            raise serializers.ValidationError({'voix': 'Langue différente de celle de la scène.'})
        if len(attrs['texte']) > settings.STUDIO_MAX_TTS_CHARS:
            raise serializers.ValidationError({'texte': 'Texte trop long.'})
        if attrs['scene'].jobs.filter(statut__in=['PENDING', 'RUNNING']).exists():
            raise serializers.ValidationError({'scene': 'Un traitement est déjà en cours.'})
        return attrs


class RenderInput(serializers.Serializer):
    # Corps JSON optionnel vide : la source de vérité est la scène.
    pass


class MediaListResponseSerializer(serializers.Serializer):
    results = MediaAssetSerializer(many=True)


class SceneListResponseSerializer(serializers.Serializer):
    results = SceneSerializer(many=True)


class VoiceListResponseSerializer(serializers.Serializer):
    results = VoiceSerializer(many=True)


class JobListResponseSerializer(serializers.Serializer):
    results = JobSerializer(many=True)


class DialogueListResponseSerializer(serializers.Serializer):
    results = DialogueSerializer(many=True)
