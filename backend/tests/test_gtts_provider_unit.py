"""Pytest unittest-style: no ElevenLabs key and no paid provider involved."""
import io
from types import SimpleNamespace
from unittest.mock import patch


def test_gtts_french_provider_without_paid_api_key(settings):
    from apps.media_studio.providers.tts import synthesize
    from gtts import gTTS

    profile = SimpleNamespace(
        provider='GTTS', model_id='gtts-fr', voice_id='fr',
        langue=SimpleNamespace(code='fr'))
    settings.STUDIO_TTS_PROVIDERS = {'GTTS'}
    settings.STUDIO_MAX_TTS_CHARS = 2500
    settings.STUDIO_MAX_TTS_RESULT_BYTES = 4_000_000
    settings.STUDIO_PROVIDER_TIMEOUT = 20

    def fake_write(instance, fp):
        fp.write(b'ID3' + b'\0' * 256)

    with patch.object(gTTS, 'write_to_fp', fake_write):
        payload, ext, mime = synthesize(profile, 'Bonjour Miora')
    assert payload.startswith(b'ID3')
    assert (ext, mime) == ('.mp3', 'audio/mpeg')


def test_gtts_not_assigned_to_malagasy(settings):
    from apps.media_studio.providers.tts import synthesize, ProviderError
    profile = SimpleNamespace(provider='GTTS', model_id='gtts-fr', voice_id='fr',langue=SimpleNamespace(code='mg'))
    settings.STUDIO_TTS_PROVIDERS = {'GTTS'}
    settings.STUDIO_MAX_TTS_CHARS = 2500
    try:
        synthesize(profile, 'Salama')
    except ProviderError as exc:
        assert exc.code == 'TTS_CONFIGURATION_INVALID'
    else:
        raise AssertionError('Must not send Malagasy to the French gTTS voice')
