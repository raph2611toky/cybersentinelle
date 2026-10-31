"""Contrat staff de lecture d'une scène, sans fournisseur TTS ni appel réseau."""
from types import SimpleNamespace
from uuid import uuid4

from apps.media_studio.models import SceneMedia
from apps.media_studio.serializers import SceneSerializer


def test_staff_scene_serializer_exposes_independent_audio_source():
    video_id, audio_id, image_id = uuid4(), uuid4(), uuid4()
    scene = SimpleNamespace(video_id=video_id, audio_id=audio_id, image_id=image_id,
                            video_finale_id=None, statut=SceneMedia.Status.DRAFT,
                            mode=SceneMedia.Mode.VIDEO_AUDIO)
    serializer = SceneSerializer()
    assert serializer.get_video_source_url(scene).endswith(f'/media/{video_id}/file/')
    assert serializer.get_audio_source_url(scene).endswith(f'/media/{audio_id}/file/')
    assert serializer.get_image_source_url(scene).endswith(f'/media/{image_id}/file/')
    assert serializer.get_audio_embedded(scene) is False


def test_final_video_with_mixed_narration_is_marked_as_embedded_audio():
    scene = SimpleNamespace(video_finale_id=uuid4(), statut=SceneMedia.Status.READY,
                            mode=SceneMedia.Mode.VIDEO_AUDIO)
    assert SceneSerializer().get_audio_embedded(scene) is True
    scene.mode = SceneMedia.Mode.IMAGE_AUDIO
    assert SceneSerializer().get_audio_embedded(scene) is True
    scene.mode = SceneMedia.Mode.VIDEO_ORIGINAL
    assert SceneSerializer().get_audio_embedded(scene) is False
    scene.mode = SceneMedia.Mode.VIDEO_AUDIO
    scene.statut = SceneMedia.Status.DRAFT
    assert SceneSerializer().get_audio_embedded(scene) is False
