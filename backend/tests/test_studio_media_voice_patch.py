"""Régression Studio audio + sélection des médias. Réseau externe systématiquement mocké."""
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.core.models import Langue
from apps.content_api.graph_service import sanitize_graph
from apps.media_studio.services.video import render_scene, probe, RenderError
from apps.media_studio.models import SceneMedia, VoiceProfile


def _draft(media):
    return {'nodes': [
        {'id': 'start', 'position': {'x': 0, 'y': 0}, 'data': {
            'kind': 'scene', 'title': {'fr': 'Miora', 'mg': ''},
            'text': {'fr': 'Introduction', 'mg': ''}, 'media': media,
        }},
        {'id': 'end', 'position': {'x': 100, 'y': 200}, 'data': {
            'kind': 'ending', 'title': {'fr': 'Fin', 'mg': ''}, 'text': {'fr': 'Fin', 'mg': ''},
        }},
    ], 'edges': [{'source': 'start', 'sourceHandle': 'out', 'target': 'end'}]}


def test_graph_sanitizer_preserves_draft_media():
    import uuid
    asset = str(uuid.uuid4())
    graph = sanitize_graph(_draft({'asset': asset, 'kind': 'IMAGE'}))
    assert graph['nodes'][0]['data']['media'] == {'asset': asset, 'kind': 'IMAGE'}


def test_graph_sanitizer_rejects_fake_media_reference():
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        sanitize_graph(_draft({'asset': 'pas-uuid', 'kind': 'VIDEO'}))


@pytest.mark.django_db
def test_voice_catalog_requires_authenticated_editor():
    resp = APIClient().get(reverse('studio-voices-catalog') + '?provider=GOOGLE_CLOUD&language=fr')
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_voice_catalog_returns_mocked_provider_results():
    get_user_model().objects.create_superuser(username='staff_voice', password='safeStrong!123')
    client = APIClient()
    user = get_user_model().objects.get(username='staff_voice')
    client.force_authenticate(user=user)
    values = [{'name':'Voix française', 'voice_id':'fr-FR-Standard-A', 'model_id':'cloud-tts', 'provider':'GOOGLE_CLOUD'}]
    with patch('apps.media_studio.views.list_provider_voices', return_value=values):
        resp = client.get(reverse('studio-voices-catalog'), {'provider':'GOOGLE_CLOUD','language':'fr'})
    assert resp.status_code == 200
    assert resp.json()['results'] == values


@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='FFmpeg absent')
def test_render_sync_works_when_audio_exceeds_video(tmp_path, settings):
    settings.STUDIO_MAX_MEDIA_SECONDS = 12
    settings.STUDIO_RENDER_TIMEOUT = 60
    settings.STUDIO_MAX_OUTPUT_BYTES = 30_000_000
    src = tmp_path / 'video.mp4'
    voice = tmp_path / 'voice.mp3'
    subprocess.run(['ffmpeg', '-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:d=1:r=25',
                    '-c:v','libx264','-pix_fmt','yuv420p',str(src)], check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=2.4',
                    '-c:a','libmp3lame',str(voice)], check=True)

    class Lines:
        def select_related(self, *args): return self
        def order_by(self, *args): return []

    scene = SimpleNamespace(
        mode=SceneMedia.Mode.VIDEO_AUDIO, video_id=1, video=SimpleNamespace(fichier=SimpleNamespace(path=str(src))),
        image_id=None, audio_id=1, audio=SimpleNamespace(fichier=SimpleNamespace(path=str(voice))), dialogues=Lines(),
        sync_mode=SceneMedia.SyncMode.SPEED, audio_trim_start_ms=0, audio_trim_end_ms=None,
    )
    payload = render_scene(scene)
    result = tmp_path / 'render.mp4'
    result.write_bytes(payload)
    # Nouvelle règle : la narration doit être accélérée pour correspondre à la vidéo, sans étirer l'image.
    info = probe(str(result))
    video_len = float(next(s for s in info['streams'] if s['codec_type'] == 'video')['duration'])
    audio_len = float(next(s for s in info['streams'] if s['codec_type'] == 'audio')['duration'])
    assert abs(video_len - audio_len) <= 0.085
    assert abs(audio_len - 1.0) <= 0.085
