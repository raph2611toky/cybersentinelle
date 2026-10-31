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
from .services.video import render_scene, render_audio_only, extract_narration, RenderError

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
    auto_render_after_tts = False
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
                # Après une synthèse explicite, préparer un rendu FFmpeg automatiquement si visuel présent.
                # Le rendu utilise l'audio existant (pas un second appel TTS payant).
                if scene.mode in {SceneMedia.Mode.IMAGE_AUDIO, SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.AUDIO_ONLY}:
                    auto_render_after_tts = True
                else:
                    auto_render_after_tts = False
        elif job.type == GenerationJob.Type.RENDER:
            audio_only = scene.mode == SceneMedia.Mode.AUDIO_ONLY
            payload = render_audio_only(scene) if audio_only else render_scene(scene)
            used_media = [scene.image, scene.video, scene.audio]
            if not scene.audio_id:
                used_media += [line.audio for line in scene.dialogues.select_related('audio')]
            asset = persist_upload(
                ContentFile(payload, name='render.mp3' if audio_only else 'render.mp4'),
                MediaAsset.Kind.AUDIO if audio_only else MediaAsset.Kind.VIDEO,
                title=f'Clip {scene.noeud.cle} {scene.langue.code}',
                licence='Montage interne à partir des médias éditoriaux vérifiés',
                langue=scene.langue, origin=MediaAsset.Origin.RENDER,
                rights_confirmed=all(x.droits_confirmes for x in used_media if x))
            if audio_only:
                scene.audio_finale = asset
                scene.video_finale = None
            else:
                scene.video_finale = asset
                scene.audio_finale = None
                if scene.mode in {SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.IMAGE_AUDIO}:
                    scene.audio_finale = persist_upload(
                        ContentFile(extract_narration(payload), name='narration.mp3'), MediaAsset.Kind.AUDIO,
                        title=f'Piste {scene.noeud.cle} {scene.langue.code}',
                        licence='Piste synchronisée du montage', langue=scene.langue,
                        origin=MediaAsset.Origin.RENDER,
                        rights_confirmed=all(x.droits_confirmes for x in used_media if x))
            scene.statut = SceneMedia.Status.READY
            scene.full_clean()
            scene.save(update_fields=['video_finale', 'audio_finale', 'statut', 'updated_at'])
        else:
            raise RenderError('JOB_TYPE_UNSUPPORTED')
        job.resultat = asset
        job.statut = GenerationJob.Status.SUCCESS
        job.fin_le = timezone.now()
        job.save(update_fields=['resultat', 'statut', 'fin_le', 'updated_at'])
        if auto_render_after_tts and job.type == GenerationJob.Type.TTS:
            # On n'envoie pas un TTS supplémentaire ; job distinct et visible dans le studio.
            render_job = GenerationJob.objects.create(type=GenerationJob.Type.RENDER, scene=scene)
            try:
                process_studio_job.delay(str(render_job.pk))
            except Exception:
                GenerationJob.objects.filter(pk=render_job.pk).update(
                    statut=GenerationJob.Status.FAILED, code_erreur='QUEUE_UNAVAILABLE', fin_le=timezone.now())
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
