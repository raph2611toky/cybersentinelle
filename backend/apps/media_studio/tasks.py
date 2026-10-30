"""Tâches Celery explicites, aucun appel IA automatique lors du GET public."""
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from celery import shared_task
from .models import GenerationJob, MediaAsset, SceneMedia
from .providers.tts import synthesize, ProviderError
from .services.media import persist_generated, persist_upload
from .services.video import render_scene, RenderError

LOG = logging.getLogger('safidiko')


@shared_task(ignore_result=True, acks_late=True)
def process_studio_job(job_id):
    # Verrouillage évitant de retraiter une tâche déjà lancée (duplicate delivery).
    with transaction.atomic():
        job = GenerationJob.objects.select_for_update().get(pk=job_id)
        if job.statut != GenerationJob.Status.PENDING:
            return
        job.statut = GenerationJob.Status.RUNNING
        job.debut_le = timezone.now()
        job.save(update_fields=['statut', 'debut_le', 'updated_at'])
    try:
        scene = SceneMedia.objects.select_related('langue', 'voix', 'image', 'video', 'audio').get(pk=job.scene_id)
        if job.type == GenerationJob.Type.TTS:
            voice = job.voix
            if not voice or voice.langue_id != scene.langue_id or not voice.actif:
                raise ProviderError('TTS_VOICE_INVALID')
            content, ext, mime = synthesize(voice, job.texte)
            asset = persist_generated(content, ext, mime, title=f'Voix {scene.noeud.cle} {scene.langue.code}',
                licence='Voix générée via fournisseur : vérifier les droits du plan',
                lang=scene.langue, provider=voice.provider)
            if job.dialogue_id:
                dialogue = job.dialogue
                dialogue.audio = asset
                dialogue.save(update_fields=['audio', 'updated_at'])
            else:
                scene.audio = asset
                scene.statut = SceneMedia.Status.DRAFT
                scene.save(update_fields=['audio', 'statut', 'updated_at'])
        elif job.type == GenerationJob.Type.RENDER:
            if (scene.mode in {SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.IMAGE_AUDIO}
                    and not scene.audio_id
                    and not (scene.dialogues.exists() and not scene.dialogues.filter(audio__isnull=True).exists())
                    and scene.voix_id and scene.narration_texte.strip()):
                voice = scene.voix
                if not voice.actif or voice.langue_id != scene.langue_id:
                    raise ProviderError('TTS_VOICE_INVALID')
                data, ext, mime = synthesize(voice, scene.narration_texte)
                narration = persist_generated(data, ext, mime,
                    title=f'Narration {scene.noeud.cle} {scene.langue.code}',
                    licence='Droits de la synthèse vocale à vérifier',
                    lang=scene.langue, provider=voice.provider)
                scene.audio = narration
                scene.save(update_fields=['audio', 'updated_at'])
            payload = render_scene(scene)
            used_media = [scene.image, scene.video, scene.audio]
            if not scene.audio_id:
                used_media += [line.audio for line in scene.dialogues.select_related('audio')]
            asset = persist_upload(ContentFile(payload, name='render.mp4'), MediaAsset.Kind.VIDEO,
                title=f'Clip {scene.noeud.cle} {scene.langue.code}',
                licence='Montage interne à partir des médias éditoriaux vérifiés',
                langue=scene.langue, origin=MediaAsset.Origin.RENDER,
                rights_confirmed=all(x.droits_confirmes for x in used_media if x))
            scene.video_finale = asset
            scene.statut = SceneMedia.Status.READY
            scene.full_clean()
            scene.save(update_fields=['video_finale', 'statut', 'updated_at'])
        else:
            raise RenderError('JOB_TYPE_UNSUPPORTED')
        job.resultat = asset
        job.statut = GenerationJob.Status.SUCCESS
        job.fin_le = timezone.now()
        job.save(update_fields=['resultat', 'statut', 'fin_le', 'updated_at'])
    except (ProviderError, RenderError) as exc:
        LOG.warning('Studio job %s: %s', job_id, exc.code)
        GenerationJob.objects.filter(pk=job_id).update(statut=GenerationJob.Status.FAILED,
            code_erreur=exc.code, fin_le=timezone.now())
        if job.type == GenerationJob.Type.RENDER:
            SceneMedia.objects.filter(pk=job.scene_id).update(statut=SceneMedia.Status.FAILED)
    except Exception:
        LOG.exception('Echec interne du travail studio %s', job_id)
        GenerationJob.objects.filter(pk=job_id).update(statut=GenerationJob.Status.FAILED,
            code_erreur='INTERNAL_ERROR', fin_le=timezone.now())
        if job.type == GenerationJob.Type.RENDER:
            SceneMedia.objects.filter(pk=job.scene_id).update(statut=SceneMedia.Status.FAILED)
