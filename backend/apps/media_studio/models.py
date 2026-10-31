"""Gestion éditoriale privée des médias ; aucune donnée de participant."""
import uuid
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Q
from apps.core.models import ModeleBase, Langue
from apps.content_api.models import Noeud


class PrivateStorage(FileSystemStorage):
    """Stockage sans URL publique (même quand DEBUG=True)."""
    def __init__(self, *args, **kwargs):
        super().__init__(location=settings.STUDIO_PRIVATE_ROOT, base_url=None, *args, **kwargs)


def studio_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()[:8]
    return f'{instance.type.lower()}/{uuid.uuid4().hex}{extension}'


class MediaAsset(ModeleBase):
    class Kind(models.TextChoices):
        IMAGE = 'IMAGE', 'Image'
        VIDEO = 'VIDEO', 'Vidéo'
        AUDIO = 'AUDIO', 'Audio'
        SUBTITLE = 'SUBTITLE', 'Sous-titres'

    class Origin(models.TextChoices):
        UPLOAD = 'UPLOAD', 'Import manuel'
        TTS = 'TTS', 'Synthèse vocale'
        RENDER = 'RENDER', 'Assemblage FFmpeg'

    titre = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=Kind.choices)
    fichier = models.FileField(storage=PrivateStorage, upload_to=studio_upload_path, max_length=250)
    mime_type = models.CharField(max_length=100)
    taille_octets = models.PositiveBigIntegerField(default=0)
    duree_ms = models.PositiveIntegerField(null=True, blank=True)
    largeur_px = models.PositiveIntegerField(null=True, blank=True)
    hauteur_px = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, db_index=True)
    origine = models.CharField(max_length=10, choices=Origin.choices, default=Origin.UPLOAD)
    provider = models.CharField(max_length=20, blank=True)
    langue = models.ForeignKey(Langue, on_delete=models.PROTECT, null=True, blank=True, related_name='media_assets')
    licence = models.CharField(max_length=160)
    droits_confirmes = models.BooleanField(default=False)

    class Meta:
        db_table = 'media_studio_asset'
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if not self.titre.strip() or not self.licence.strip():
            raise ValidationError('Titre et licence sont obligatoires.')
        if not self.droits_confirmes and self.origine == self.Origin.UPLOAD:
            raise ValidationError('Confirmer la provenance et les droits pour un upload.')

    def __str__(self):
        return f'{self.type}: {self.titre}'


class VoiceProfile(ModeleBase):
    class Provider(models.TextChoices):
        GTTS = 'GTTS', 'gTTS (Google Traduction, français)'
        GEMINI = 'GEMINI', 'Gemini Developer API'
        ELEVENLABS = 'ELEVENLABS', 'ElevenLabs'
        GOOGLE_CLOUD = 'GOOGLE_CLOUD', 'Google Cloud Text-to-Speech'

    nom = models.CharField(max_length=100)
    langue = models.ForeignKey(Langue, on_delete=models.PROTECT, related_name='voix_studio')
    provider = models.CharField(max_length=12, choices=Provider.choices)
    model_id = models.CharField(max_length=100)
    voice_id = models.CharField(max_length=120)
    style = models.CharField(max_length=150, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'media_studio_voice'
        ordering = ['langue__code', 'nom']
        constraints = [models.UniqueConstraint(fields=['langue', 'provider', 'model_id', 'voice_id'], name='studio_unique_voice')]

    def __str__(self):
        return f'{self.nom} ({self.langue.code}, {self.provider})'


class SceneMedia(ModeleBase):
    class Mode(models.TextChoices):
        VIDEO_ORIGINAL = 'VIDEO_ORIGINAL', 'Vidéo avec audio incorporé'
        VIDEO_AUDIO = 'VIDEO_AUDIO', 'Vidéo et audio séparés'
        IMAGE_AUDIO = 'IMAGE_AUDIO', 'Image et audio'
        AUDIO_ONLY = 'AUDIO_ONLY', 'Audio seul'
        TEXT_ONLY = 'TEXT_ONLY', 'Texte uniquement'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Brouillon'
        READY = 'READY', 'Prêt à publier'
        PROCESSING = 'PROCESSING', 'Rendu en cours'
        FAILED = 'FAILED', 'Échec du rendu'

    noeud = models.ForeignKey(Noeud, on_delete=models.CASCADE, related_name='scene_media')
    langue = models.ForeignKey(Langue, on_delete=models.PROTECT, related_name='scene_media')
    mode = models.CharField(max_length=18, choices=Mode.choices, default=Mode.TEXT_ONLY)
    image = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_images')
    video = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_videos')
    audio = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_audios')
    sous_titres = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_subtitles')
    video_finale = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_renders')
    audio_finale = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_audio_renders')

    class SyncMode(models.TextChoices):
        FREEZE_LAST = 'FREEZE_LAST', 'Durées libres : figer la dernière image après la vidéo'
        SPEED = 'SPEED', 'Vitesse pour ajuster la narration entière'
        TRIM = 'TRIM', 'Découper un segment (vitesse normale)'
        TRIM_SPEED = 'TRIM_SPEED', 'Découper puis ajuster la vitesse'

    sync_mode = models.CharField(max_length=12, choices=SyncMode.choices, default=SyncMode.FREEZE_LAST)
    audio_trim_start_ms = models.PositiveIntegerField(default=0)
    audio_trim_end_ms = models.PositiveIntegerField(null=True, blank=True)

    narration_texte = models.TextField(blank=True)
    voix = models.ForeignKey(VoiceProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='scenes')
    statut = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        db_table = 'media_studio_scene'
        ordering = ['noeud__cle', 'langue__code']
        constraints = [models.UniqueConstraint(fields=['noeud', 'langue'], name='studio_unique_node_lang')]

    def clean(self):
        super().clean()
        if self.noeud_id and self.noeud.type not in ('SCENE', 'ENDING'):
            raise ValidationError({'noeud': 'Une vidéo ou une narration ne peut être associée qu’à une scène ou une fin.'})
        checks = [('image', MediaAsset.Kind.IMAGE), ('video', MediaAsset.Kind.VIDEO),
                  ('audio', MediaAsset.Kind.AUDIO), ('sous_titres', MediaAsset.Kind.SUBTITLE),
                  ('video_finale', MediaAsset.Kind.VIDEO), ('audio_finale', MediaAsset.Kind.AUDIO)]
        for attr, expected in checks:
            media = getattr(self, attr, None)
            if media and media.type != expected:
                raise ValidationError({attr: f'Le média doit être de type {expected}.'})
        if self.voix_id and self.voix.langue_id != self.langue_id:
            raise ValidationError({'voix': 'La langue de la voix ne correspond pas à la scène.'})
        if self.mode == self.Mode.VIDEO_ORIGINAL and not self.video_id:
            raise ValidationError({'video': 'Vidéo requise.'})
        if self.mode == self.Mode.VIDEO_AUDIO and not self.video_id:
            raise ValidationError({'video': 'Vidéo requise.'})
        if self.mode == self.Mode.IMAGE_AUDIO and not self.image_id:
            raise ValidationError({'image': 'Image requise.'})
        if self.audio_trim_end_ms is not None and self.audio_trim_end_ms <= self.audio_trim_start_ms:
            raise ValidationError({'audio_trim_end_ms': 'La fin doit être après le début du segment.'})
        if self.mode == self.Mode.AUDIO_ONLY and (self.image_id or self.video_id):
            raise ValidationError({'mode': 'Le mode audio seul ne doit pas contenir de visuel.'})
        if self.statut == self.Status.READY:
            if self.mode == self.Mode.AUDIO_ONLY and not self.audio_finale_id:
                raise ValidationError('Un rendu audio final est nécessaire avant publication.')
            if self.mode not in {self.Mode.TEXT_ONLY, self.Mode.AUDIO_ONLY} and not self.video_finale_id:
                raise ValidationError('Un rendu vidéo final est nécessaire avant publication.')

    def __str__(self):
        return f'{self.noeud.tantara.slug}:{self.noeud.cle}/{self.langue.code}'


class DialogueLine(ModeleBase):
    scene = models.ForeignKey(SceneMedia, on_delete=models.CASCADE, related_name='dialogues')
    ordre = models.PositiveSmallIntegerField()
    personnage = models.CharField(max_length=80, blank=True)
    texte = models.TextField()
    voix = models.ForeignKey(VoiceProfile, on_delete=models.PROTECT, null=True, blank=True, related_name='dialogues')
    audio = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, null=True, blank=True, related_name='dialogues')

    class Meta:
        db_table = 'media_studio_dialogue'
        ordering = ['ordre']
        constraints = [models.UniqueConstraint(fields=['scene', 'ordre'], name='studio_unique_line_order')]

    def clean(self):
        super().clean()
        if not self.texte.strip():
            raise ValidationError({'texte': 'Texte obligatoire.'})
        if self.voix_id and self.voix.langue_id != self.scene.langue_id:
            raise ValidationError({'voix': 'Voix dans une autre langue.'})
        if self.audio_id and self.audio.type != MediaAsset.Kind.AUDIO:
            raise ValidationError({'audio': 'Un fichier audio est nécessaire.'})


class SceneAudioVariant(ModeleBase):
    """Pistes alternatives privées d'une même scène, sans écraser la piste active."""
    class Origin(models.TextChoices):
        TTS = 'TTS', 'Synthèse vocale'
        FILE = 'FILE', 'Fichier audio'
        LEGACY = 'LEGACY', 'Piste préexistante'

    scene = models.ForeignKey(SceneMedia, on_delete=models.CASCADE, related_name='variants')
    titre = models.CharField(max_length=160)
    origine = models.CharField(max_length=10, choices=Origin.choices, default=Origin.FILE)
    audio = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name='scene_variants')
    voix = models.ForeignKey(VoiceProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='audio_variants')
    texte = models.TextField(blank=True)
    selected = models.BooleanField(default=False)
    activate_on_ready = models.BooleanField(default=True)
    sync_mode = models.CharField(max_length=12, choices=SceneMedia.SyncMode.choices, default=SceneMedia.SyncMode.FREEZE_LAST)
    audio_trim_start_ms = models.PositiveIntegerField(default=0)
    audio_trim_end_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'media_studio_variant'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['scene', 'created_at'], name='studio_variant_scene_idx')]

    def clean(self):
        super().clean()
        if self.audio_id and self.audio.type != MediaAsset.Kind.AUDIO:
            raise ValidationError({'audio': 'Ce fichier doit être audio.'})
        if self.voix_id and self.scene_id and self.voix.langue_id != self.scene.langue_id:
            raise ValidationError({'voix': 'La voix doit correspondre à la langue de la scène.'})
        if self.audio_trim_end_ms is not None and self.audio_trim_end_ms <= self.audio_trim_start_ms:
            raise ValidationError({'audio_trim_end_ms': 'La fin doit être après le début.'})


class GenerationJob(ModeleBase):
    class Type(models.TextChoices):
        TTS = 'TTS', 'Synthèse vocale'
        RENDER = 'RENDER', 'Rendu vidéo local'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        RUNNING = 'RUNNING', 'Exécution'
        SUCCESS = 'SUCCESS', 'Terminé'
        FAILED = 'FAILED', 'Échec'

    type = models.CharField(max_length=8, choices=Type.choices)
    statut = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    scene = models.ForeignKey(SceneMedia, on_delete=models.CASCADE, related_name='jobs')
    variante = models.ForeignKey(SceneAudioVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    dialogue = models.ForeignKey(DialogueLine, on_delete=models.CASCADE, null=True, blank=True, related_name='jobs')
    voix = models.ForeignKey(VoiceProfile, on_delete=models.PROTECT, null=True, blank=True)
    texte = models.TextField(blank=True)
    resultat = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, null=True, blank=True, related_name='jobs')
    code_erreur = models.CharField(max_length=60, blank=True)
    debut_le = models.DateTimeField(null=True, blank=True)
    fin_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'media_studio_job'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['statut', 'created_at'], name='studio_job_status_idx')]

    def __str__(self):
        return f'{self.type}: {self.statut}'
