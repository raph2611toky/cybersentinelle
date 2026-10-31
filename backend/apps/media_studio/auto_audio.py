"""Prepare a persistent French narration on editorial writes, never public reads."""
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import SceneMedia, VoiceProfile, GenerationJob

LOG = logging.getLogger('safidiko')


def dispatch(job_id):
    from .tasks import process_studio_job
    try:
        process_studio_job.delay(str(job_id))
    except Exception:
        LOG.exception('Automatic narration queue unavailable')
        GenerationJob.objects.filter(pk=job_id).update(statut='FAILED', code_erreur='QUEUE_UNAVAILABLE', fin_le=timezone.now())


def prepare_audio(scene_id):
    """Idempotent per scene; keep imported audio and pending work intact."""
    with transaction.atomic():
        scene = SceneMedia.objects.select_for_update().select_related('noeud', 'langue', 'voix').get(pk=scene_id)
        if scene.audio_id or scene.jobs.filter(statut__in=['PENDING', 'RUNNING']).exists():
            return None
        code = scene.langue.code
        text = scene.narration_texte.strip() or (scene.noeud.texte_fr.strip() if code == 'fr' else '')
        if not text:
            return 'NARRATION_TEXT_MISSING'
        voice = scene.voix or VoiceProfile.objects.filter(langue=scene.langue, actif=True).order_by('created_at').first()
        if not voice or not voice.actif or voice.langue_id != scene.langue_id:
            return 'TTS_VOICE_MISSING'
        if len(text) > settings.STUDIO_MAX_TTS_CHARS:
            return 'TTS_TEXT_TOO_LONG'
        # Lock the chosen profile to serialize automatic quota reservations.
        VoiceProfile.objects.select_for_update().get(pk=voice.pk)
        if GenerationJob.objects.filter(type='TTS', created_at__date=timezone.localdate()).count() >= settings.STUDIO_TTS_DAILY_LIMIT:
            return 'TTS_DAILY_LIMIT'
        mode = 'VIDEO_AUDIO' if scene.video_id else 'IMAGE_AUDIO' if scene.image_id else 'AUDIO_ONLY'
        SceneMedia.objects.filter(pk=scene.pk).update(mode=mode, voix=voice, narration_texte=text,
            video_finale=None, audio_finale=None, statut='DRAFT', updated_at=timezone.now())
        job = GenerationJob.objects.create(type='TTS', scene=scene, voix=voice, texte=text)
        transaction.on_commit(lambda: dispatch(job.pk))
        return None


def ensure_node_audio(node_id):
    from apps.content_api.models import Noeud
    from apps.core.models import Langue
    node = Noeud.objects.filter(pk=node_id, type__in=['SCENE','ENDING']).first()
    language = Langue.objects.filter(code='fr', actif=True).first()
    if not node or not language:
        return 'FRENCH_LANGUAGE_MISSING'
    scene, _ = SceneMedia.objects.get_or_create(noeud=node, langue=language)
    return prepare_audio(scene.pk)
