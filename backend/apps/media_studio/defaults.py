"""Shared policy: free gTTS FR is the default, paid providers remain opt-in."""
from .models import VoiceProfile


def default_french_voice(langue):
    if langue.code != 'fr':
        return None
    voice, _ = VoiceProfile.objects.get_or_create(
        langue=langue, provider='GTTS', model_id='gtts-fr', voice_id='fr',
        defaults={'nom': 'gTTS français (défaut)', 'actif': True},
    )
    return voice if voice.actif else None
