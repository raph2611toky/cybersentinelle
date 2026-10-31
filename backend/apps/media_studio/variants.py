"""Alternative narration management, preserving other audio assets and choices."""
from django.db import transaction
from .models import SceneAudioVariant, SceneMedia, GenerationJob


def sync_selected_file(scene):
    """After a direct scene edit, remember a manually attached file, never delete old variants."""
    SceneAudioVariant.objects.filter(scene=scene, selected=True).update(selected=False)
    if not scene.audio_id:
        return None
    variant = SceneAudioVariant.objects.filter(scene=scene, audio_id=scene.audio_id).first()
    if not variant:
        variant = SceneAudioVariant.objects.create(
            scene=scene, titre=getattr(scene.audio, 'titre', 'Piste importée')[:160],
            origine=SceneAudioVariant.Origin.FILE, audio=scene.audio,
            voix=scene.voix, texte=scene.narration_texte,
            sync_mode=scene.sync_mode,
            audio_trim_start_ms=scene.audio_trim_start_ms,
            audio_trim_end_ms=scene.audio_trim_end_ms,
            selected=True)
    else:
        variant.selected = True
        variant.sync_mode = scene.sync_mode
        variant.audio_trim_start_ms = scene.audio_trim_start_ms
        variant.audio_trim_end_ms = scene.audio_trim_end_ms
        variant.save(update_fields=['selected', 'sync_mode', 'audio_trim_start_ms', 'audio_trim_end_ms', 'updated_at'])
    return variant


def select_variant(scene, variant=None):
    """Transaction caller must hold SceneMedia row lock. None means no active audio."""
    if variant is not None and (variant.scene_id != scene.pk or not variant.audio_id):
        raise ValueError('Cette piste n’est pas prête ou ne correspond pas à la scène.')
    SceneAudioVariant.objects.filter(scene=scene, selected=True).update(selected=False)
    if variant is not None:
        variant.selected = True
        variant.save(update_fields=['selected', 'updated_at'])
        scene.audio_id = variant.audio_id
        scene.voix_id = variant.voix_id
        scene.narration_texte = variant.texte
        scene.sync_mode = variant.sync_mode
        scene.audio_trim_start_ms = variant.audio_trim_start_ms
        scene.audio_trim_end_ms = variant.audio_trim_end_ms
        scene.mode = (SceneMedia.Mode.VIDEO_AUDIO if scene.video_id else
                      SceneMedia.Mode.IMAGE_AUDIO if scene.image_id else SceneMedia.Mode.AUDIO_ONLY)
    else:
        scene.audio = None
        scene.voix = None
        scene.narration_texte = ''
        scene.mode = SceneMedia.Mode.TEXT_ONLY if not (scene.video_id or scene.image_id) else scene.mode
    scene.audio_finale = None
    scene.video_finale = None
    scene.statut = SceneMedia.Status.DRAFT
    scene.save(update_fields=['audio','voix','narration_texte','sync_mode',
        'audio_trim_start_ms','audio_trim_end_ms','audio_finale','video_finale','statut','mode','updated_at'])
    return scene
