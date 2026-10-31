from unittest.mock import patch
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.core.models import Langue
from apps.content_api.models import Noeud
from apps.media_studio.models import SceneMedia, VoiceProfile, GenerationJob, MediaAsset
from apps.media_studio.auto_audio import ensure_node_audio, prepare_audio
from apps.media_studio.serializers import SceneSerializer
from tests.test_dashboard_integration import _story

pytestmark = pytest.mark.django_db


def setup_scene():
    fr = Langue.objects.create(code='fr', nom_fr='Français', nom_mg='Frantsay', nom_natif='Français')
    node = Noeud.objects.create(tantara=_story(), cle='start', type='ENDING', titre_fr='Début', titre_mg='Fiandohana', texte_fr='Une description à lire.', texte_mg='Lahatsoratra.')
    voice = VoiceProfile.objects.create(nom='FR', langue=fr, provider='ELEVENLABS', model_id='test', voice_id='test')
    return node, fr, voice


def test_missing_fr_uses_description_once_and_mg_stays_optional():
    node, fr, voice = setup_scene()
    with patch('apps.media_studio.auto_audio.dispatch'):
        assert ensure_node_audio(node.pk) is None
        assert ensure_node_audio(node.pk) is None
    scene = SceneMedia.objects.get(noeud=node, langue=fr)
    assert scene.mode == 'AUDIO_ONLY'
    assert scene.narration_texte == node.texte_fr
    assert GenerationJob.objects.filter(scene=scene, type='TTS').count() == 1
    assert not SceneMedia.objects.filter(noeud=node, langue__code='mg').exists()


def test_imported_audio_is_never_replaced():
    node, fr, voice = setup_scene()
    asset = MediaAsset.objects.create(titre='Import', type='AUDIO', mime_type='audio/mpeg', taille_octets=1, sha256='0'*64, licence='Original', droits_confirmes=True)
    scene = SceneMedia.objects.create(noeud=node, langue=fr, mode='AUDIO_ONLY', audio=asset)
    assert prepare_audio(scene.pk) is None
    assert not GenerationJob.objects.exists()
    scene.refresh_from_db()
    assert scene.audio_id == asset.pk


def test_missing_voice_returns_actionable_reason_without_job():
    node, fr, voice = setup_scene()
    voice.delete()
    assert ensure_node_audio(node.pk) == 'TTS_VOICE_MISSING'
    assert not GenerationJob.objects.exists()


def test_supplied_malagasy_text_generates_matching_voice():
    node, fr, voice = setup_scene()
    mg = Langue.objects.create(code='mg', nom_fr='Malgache', nom_mg='Malagasy', nom_natif='Malagasy')
    mgvoice = VoiceProfile.objects.create(nom='MG', langue=mg, provider='ELEVENLABS', model_id='test', voice_id='test')
    scene = SceneMedia.objects.create(noeud=node, langue=mg, mode='AUDIO_ONLY', narration_texte='Salama', voix=mgvoice)
    assert prepare_audio(scene.pk) is None
    job = GenerationJob.objects.get(scene=scene)
    assert job.voix_id == mgvoice.pk and job.texte == 'Salama'


def test_staff_contract_contains_both_tracks_with_null_optional_mg():
    node, fr, voice = setup_scene()
    asset = MediaAsset.objects.create(titre='Import', type='AUDIO', mime_type='audio/mpeg', taille_octets=1, sha256='0'*64, licence='Original', droits_confirmes=True)
    scene = SceneMedia.objects.create(noeud=node, langue=fr, mode='AUDIO_ONLY', audio=asset)
    tracks = SceneSerializer(scene).data['audio_tracks']
    assert tracks['mg'] is None
    assert str(asset.pk) in tracks['fr']['url']


def test_prepare_endpoint_requires_staff():
    node, fr, voice = setup_scene()
    url = f'/api/editor/studio/stories/{node.tantara_id}/prepare-audio/'
    client = Client()
    assert client.post(url, {}, content_type='application/json').status_code in (401,403)
    client.force_login(get_user_model().objects.create_superuser('audio', password='testing-secret'))
    response = client.post(url, {}, content_type='application/json')
    assert response.status_code == 202
    assert response.json()['results'][0]['error'] is None


def test_post_commit_write_schedules_one_job(django_capture_on_commit_callbacks):
    with patch('apps.media_studio.auto_audio.dispatch') as dispatch:
        with django_capture_on_commit_callbacks(execute=True):
            node, fr, voice = setup_scene()
        assert GenerationJob.objects.filter(scene__noeud=node).count() == 1
        assert dispatch.call_count == 1


def test_extract_track_preserves_render_timeline(tmp_path):
    import subprocess
    from apps.media_studio.services.video import extract_narration, duration_sec
    clip = tmp_path / 'clip.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x120:d=1',
                    '-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-c:a','aac','-shortest',str(clip)], check=True)
    track = tmp_path / 'track.mp3'
    track.write_bytes(extract_narration(clip.read_bytes()))
    assert abs(duration_sec(str(track), 'audio') - duration_sec(str(clip), 'video')) < .1


def test_public_payload_returns_both_language_urls_without_private_paths():
    from uuid import uuid4
    from django.test import RequestFactory
    from apps.publication.services import decorate_story_urls
    fr, mg = uuid4(), uuid4()
    data = {'id':'demo', 'nodes':{'start':{'media':{
        'fr':{'mode':'video','audio_path':f'media/{fr}.mp3'},
        'mg':{'mode':'video','audio_path':f'media/{mg}.mp3'},
    }}}}
    result = decorate_story_urls(data, {'version':'test-v1','files':[]}, RequestFactory().get('/'))
    node = result['nodes']['start']
    assert node['default_audio_language'] == 'fr'
    assert str(fr) in node['audio_tracks']['fr']['url']
    assert str(mg) in node['audio_tracks']['mg']['url']
    assert 'audio_path' not in node['media']['fr']
