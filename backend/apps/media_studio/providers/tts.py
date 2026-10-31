"""Adaptateurs TTS. Ne jamais logger les textes, clés ou réponses externes."""
import base64
import json
import os
import re
import urllib.error
import urllib.request
import urllib.parse
from django.conf import settings


class ProviderError(Exception):
    def __init__(self, code='TTS_UNAVAILABLE'):
        self.code = code
        super().__init__(code)


def _post_json(url, api_key_header, api_key, payload, *, audio=False):
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', api_key_header: api_key}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=settings.STUDIO_PROVIDER_TIMEOUT) as response:
            body = response.read(settings.STUDIO_MAX_TTS_RESULT_BYTES + 1)
            if len(body) > settings.STUDIO_MAX_TTS_RESULT_BYTES:
                raise ProviderError('TTS_RESULT_TOO_LARGE')
            return body if audio else json.loads(body)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise ProviderError('TTS_QUOTA_EXCEEDED') from None
        raise ProviderError('TTS_PROVIDER_ERROR') from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ProviderError('TTS_UNAVAILABLE') from None


def synthesize(profile, text):
    """Retourne (bytes, ext, mime). Aucun fallback silencieux sur un fournisseur payant."""
    text = text.strip()
    if not text or len(text) > settings.STUDIO_MAX_TTS_CHARS:
        raise ProviderError('TTS_TEXT_LENGTH')
    provider = profile.provider
    if provider not in settings.STUDIO_TTS_PROVIDERS:
        raise ProviderError('TTS_PROVIDER_DISABLED')
    if profile.langue.code not in {'fr', 'mg'}:
        raise ProviderError('TTS_LANGUAGE_UNSUPPORTED')
    # Toute valeur de modèle/voix est validée car elle est stockée en BDD et sert à l'appel API.
    if not re.fullmatch(r'[A-Za-z0-9_.-]{2,120}', profile.model_id) or not re.fullmatch(r'[A-Za-z0-9_.-]{2,120}', profile.voice_id):
        raise ProviderError('TTS_CONFIGURATION_INVALID')
    if provider == 'ELEVENLABS':
        key = os.getenv('ELEVENLABS_API_KEY', '').strip()
        if not key:
            raise ProviderError('TTS_KEY_MISSING')
        # ElevenLabs ne certifie pas ici une voix malgache : essai uniquement sur validation humaine.
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{profile.voice_id}?output_format=mp3_44100_128'
        payload = {'text': text, 'model_id': profile.model_id}
        data = _post_json(url, 'xi-api-key', key, payload, audio=True)
        if len(data) < 100:
            raise ProviderError('TTS_BAD_AUDIO')
        return data, '.mp3', 'audio/mpeg'
    if provider == 'GEMINI':
        key = os.getenv('GEMINI_API_KEY', '').strip()
        if not key:
            raise ProviderError('TTS_KEY_MISSING')
        # Gemini Developer API Interactions: réponse WAV non-streaming officielle.
        payload = {
            'model': profile.model_id,
            'input': [{'type': 'user_input', 'content': [{
                'type': 'text', 'text': text,
                'annotations': [{'type': 'speech_metadata', 'style': profile.style or 'clear, gentle educational narration'}],
            }]}],
            'response_format': {'type': 'audio'},
            'generation_config': {'speech_config': [{'voice': profile.voice_id}]},
        }
        response = _post_json('https://generativelanguage.googleapis.com/v1beta/interactions',
            'x-goog-api-key', key, payload)
        try:
            audio_blocks = [item['data'] for step in response.get('steps', [])
                if step.get('type') == 'model_output'
                for item in step.get('content', []) if item.get('type') == 'audio']
            if not audio_blocks:
                raise ValueError('no audio')
            data = base64.b64decode(audio_blocks[-1], validate=True)
            if len(data) > settings.STUDIO_MAX_TTS_RESULT_BYTES or not data.startswith(b'RIFF') or data[8:12] != b'WAVE':
                raise ValueError('not WAV')
            return data, '.wav', 'audio/wav'
        except (ValueError, TypeError, KeyError, base64.binascii.Error):
            raise ProviderError('TTS_BAD_AUDIO') from None
    if provider == 'GOOGLE_CLOUD':
        # Les identifiants GCP existants sont utilisés (service account), jamais une clé placée dans l'URL.
        import google.auth
        from google.auth.transport.requests import Request
        try:
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            if not credentials.valid:
                credentials.refresh(Request())
        except Exception:
            raise ProviderError('TTS_GOOGLE_CREDENTIALS') from None
        locale = {'fr': 'fr-FR', 'mg': 'mg-MG'}[profile.langue.code]
        req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize',
            data=json.dumps({'input': {'text': text},
                             'voice': {'languageCode': locale, 'name': profile.voice_id},
                             'audioConfig': {'audioEncoding': 'MP3', 'speakingRate': 1.0}}).encode('utf-8'),
            method='POST', headers={'Authorization': f'Bearer {credentials.token}', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=settings.STUDIO_PROVIDER_TIMEOUT) as response:
                result = json.load(response)
            data = base64.b64decode(result['audioContent'], validate=True)
            if not data or len(data) > settings.STUDIO_MAX_TTS_RESULT_BYTES:
                raise ProviderError('TTS_BAD_AUDIO')
            return data, '.mp3', 'audio/mpeg'
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise ProviderError('TTS_QUOTA_EXCEEDED') from None
            raise ProviderError('TTS_PROVIDER_ERROR') from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
            raise ProviderError('TTS_UNAVAILABLE') from None
    raise ProviderError('TTS_PROVIDER_DISABLED')



def list_provider_voices(provider, language):
    """Returns only voices exposed to this authenticated account; no fake/unlimited voices."""
    if provider not in {'ELEVENLABS', 'GOOGLE_CLOUD'} or language not in {'fr', 'mg'}:
        raise ProviderError('TTS_CONFIGURATION_INVALID')
    if provider not in settings.STUDIO_TTS_PROVIDERS:
        raise ProviderError('TTS_PROVIDER_DISABLED')
    if provider == 'ELEVENLABS':
        key = os.getenv('ELEVENLABS_API_KEY', '').strip()
        if not key:
            raise ProviderError('TTS_KEY_MISSING')
        results = []
        page_token = None
        for _ in range(4):  # borne de sécurité : 4 pages de 25 voix max
            params = {'page_size': 25}
            if page_token:
                params['next_page_token'] = page_token
            url = 'https://api.elevenlabs.io/v2/voices?' + urllib.parse.urlencode(params)
            request = urllib.request.Request(url, headers={'xi-api-key': key})
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.load(response)
            except urllib.error.HTTPError as exc:
                raise ProviderError('TTS_QUOTA_EXCEEDED' if exc.code == 429 else 'TTS_PROVIDER_ERROR') from None
            except (urllib.error.URLError, OSError, TimeoutError, ValueError):
                raise ProviderError('TTS_UNAVAILABLE') from None
            for v in payload.get('voices', []):
                if not v.get('voice_id') or not v.get('name'):
                    continue
                # API free: shared Voice Library entries can be unavailable; do not declare them free.
                tier = v.get('available_for_tiers')
                if isinstance(tier, list) and tier and 'free' not in [s.lower() for s in tier]:
                    continue
                results.append({'name': v['name'][:100], 'voice_id': v['voice_id'],
                                'model_id': 'eleven_multilingual_v2', 'provider': provider,
                                'note': 'Disponibilité et consommation vérifiées à la synthèse'})
            page_token = payload.get('next_page_token') if payload.get('has_more') else None
            if not page_token:
                break
        return results
    # Google Cloud: voix officielles de l'API, sans présumer la disponibilité de mg-MG.
    import google.auth
    from google.auth.transport.requests import Request
    try:
        credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        if not credentials.valid:
            credentials.refresh(Request())
    except Exception:
        raise ProviderError('TTS_GOOGLE_CREDENTIALS') from None
    locale = {'fr': 'fr-FR', 'mg': 'mg-MG'}[language]
    url = 'https://texttospeech.googleapis.com/v1/voices?' + urllib.parse.urlencode({'languageCode': locale})
    request = urllib.request.Request(url, headers={'Authorization': f'Bearer {credentials.token}'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ProviderError('TTS_QUOTA_EXCEEDED' if exc.code == 429 else 'TTS_PROVIDER_ERROR') from None
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        raise ProviderError('TTS_UNAVAILABLE') from None
    return [{'name': v['name'], 'voice_id': v['name'], 'model_id': 'cloud-tts', 'provider': provider,
             'note': 'Tarification Google Cloud selon le modèle et les quotas'}
            for v in payload.get('voices', []) if v.get('name') and '-Standard-' in v['name'] and locale in v.get('languageCodes', [])][:100]
