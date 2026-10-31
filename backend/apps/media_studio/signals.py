"""Schedule after commit so graph application can attach visuals first."""
import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.content_api.models import Noeud
from .models import SceneMedia


def safely_prepare(callback, identifier):
    try:
        callback(identifier)
    except Exception:
        logging.getLogger('safidiko').exception('Automatic narration preparation failed')


@receiver(post_save, sender=Noeud)
def node_saved(sender, instance, raw=False, **kwargs):
    if not raw and instance.type in ('SCENE', 'ENDING'):
        from .auto_audio import ensure_node_audio
        transaction.on_commit(lambda: safely_prepare(ensure_node_audio, instance.pk))


@receiver(post_save, sender=SceneMedia)
def scene_saved(sender, instance, raw=False, **kwargs):
    if not raw and not instance.audio_id and (instance.langue.code == 'fr' or instance.narration_texte.strip()):
        from .auto_audio import prepare_audio
        transaction.on_commit(lambda: safely_prepare(prepare_audio, instance.pk))
