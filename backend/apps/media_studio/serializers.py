"""Serializers d'édition : IDs internes conservés uniquement côté staff."""
from django.urls import reverse
from rest_framework import serializers
from drf_yasg.utils import swagger_serializer_method
from apps.core.serializers import ValidatedModelSerializer
from .models import MediaAsset, VoiceProfile, SceneMedia, SceneAudioVariant, DialogueLine, GenerationJob


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
    def validate(self, attrs):
        language = attrs.get('langue', getattr(self.instance, 'langue', None))
        provider = attrs.get('provider', getattr(self.instance, 'provider', None))
        model_id = attrs.get('model_id', getattr(self.instance, 'model_id', None))
        voice_id = attrs.get('voice_id', getattr(self.instance, 'voice_id', None))
        if provider == 'GTTS' and (not language or language.code != 'fr' or model_id != 'gtts-fr' or voice_id != 'fr'):
            raise serializers.ValidationError({'provider': 'gTTS utilise uniquement français, model_id=gtts-fr, voice_id=fr.'})
        return super().validate(attrs)

    class Meta:
        model = VoiceProfile
        fields = ('id', 'nom', 'langue', 'provider', 'model_id', 'voice_id', 'style', 'actif', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class AudioVariantSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    job_status = serializers.SerializerMethodField()
    job_error = serializers.SerializerMethodField()
    voice_provider = serializers.CharField(source='voix.provider', read_only=True, default='')
    class Meta:
        model = SceneAudioVariant
        fields = ('id','scene','titre','origine','audio','audio_url','voix','voice_provider','texte',
                  'selected','activate_on_ready','sync_mode','audio_trim_start_ms','audio_trim_end_ms',
                  'job_status','job_error','created_at')
        read_only_fields = fields

    def get_audio_url(self, obj):
        if not obj.audio_id:
            return None
        path = reverse('studio-media-download', kwargs={'pk': obj.audio_id})
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path

    def get_job_status(self, obj):
        job = next(iter(obj.jobs.all()), None)
        return job.statut if job else ('SUCCESS' if obj.audio_id else 'PENDING')

    def get_job_error(self, obj):
        job = next(iter(obj.jobs.all()), None)
        return job.code_erreur if job else ''


class SceneSerializer(ValidatedModelSerializer):
    video_finale_url = serializers.SerializerMethodField()
    audio_finale_url = serializers.SerializerMethodField()
    audio_source_url = serializers.SerializerMethodField()
    video_source_url = serializers.SerializerMethodField()
    image_source_url = serializers.SerializerMethodField()
    audio_embedded = serializers.SerializerMethodField()
    audio_tracks = serializers.SerializerMethodField()
    audio_variants = AudioVariantSerializer(source='variants', many=True, read_only=True)

    class Meta:
        model = SceneMedia
        fields = ('id', 'noeud', 'langue', 'mode', 'image', 'video', 'audio', 'sous_titres',
                  'video_finale', 'video_finale_url', 'audio_finale', 'audio_finale_url',
                  'video_source_url', 'image_source_url', 'audio_source_url', 'audio_embedded', 'audio_tracks', 'audio_variants',
                  'sync_mode', 'audio_trim_start_ms', 'audio_trim_end_ms', 'narration_texte', 'voix', 'statut', 'created_at', 'updated_at')
        read_only_fields = ('id', 'video_finale', 'video_finale_url', 'audio_finale', 'audio_finale_url', 'video_source_url', 'image_source_url', 'audio_source_url', 'audio_embedded', 'audio_tracks', 'audio_variants', 'statut', 'created_at', 'updated_at')

    @swagger_serializer_method(serializer_or_field=serializers.JSONField())
    def get_audio_tracks(self, obj):
        tracks = {'fr': None, 'mg': None}
        for scene in obj.noeud.scene_media.select_related('langue').all():
            code = scene.langue.code
            if code in tracks and (scene.audio_id or scene.audio_finale_id):
                tracks[code] = {'url': self._asset_url(scene.audio_finale_id or scene.audio_id),
                                'status': scene.statut, 'synchronized': bool(scene.audio_finale_id)}
        return tracks

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
        fields = ('id', 'type', 'statut', 'scene', 'dialogue', 'variante', 'voix', 'resultat', 'resultat_url', 'code_erreur', 'debut_le', 'fin_le', 'created_at')
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
    activer = serializers.BooleanField(default=True, required=False)
    titre = serializers.CharField(max_length=160, required=False, allow_blank=True)
    sync_mode = serializers.ChoiceField(choices=SceneMedia.SyncMode.choices, required=False)
    audio_trim_start_ms = serializers.IntegerField(min_value=0, required=False, default=0)
    audio_trim_end_ms = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    scene = serializers.PrimaryKeyRelatedField(queryset=SceneMedia.objects.all())
    voix = serializers.PrimaryKeyRelatedField(queryset=VoiceProfile.objects.filter(actif=True))
    texte = serializers.CharField(max_length=2500, trim_whitespace=True, allow_blank=False)

    def validate(self, attrs):
        from django.conf import settings
        if attrs['scene'].langue_id != attrs['voix'].langue_id:
            raise serializers.ValidationError({'voix': 'Langue différente de celle de la scène.'})
        if len(attrs['texte']) > settings.STUDIO_MAX_TTS_CHARS:
            raise serializers.ValidationError({'texte': 'Texte trop long.'})
        if attrs['audio_trim_end_ms'] is not None and attrs['audio_trim_end_ms'] <= attrs['audio_trim_start_ms']:
            raise serializers.ValidationError({'audio_trim_end_ms': 'La fin doit être après le début.'})
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


class AudioVariantListResponseSerializer(serializers.Serializer):
    results = AudioVariantSerializer(many=True)
