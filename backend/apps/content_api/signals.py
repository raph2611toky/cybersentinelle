"""Nettoyage des couvertures non référencées après commit SQL réussi."""
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Tantara


def _delete_on_commit(field, name):
    if name:
        storage = field.storage
        transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=Tantara)
def remember_old_cover(sender, instance, **kwargs):
    instance._old_cover_name = None
    if instance.pk:
        instance._old_cover_name = (sender.objects.filter(pk=instance.pk)
                                    .values_list("image_cover", flat=True).first())


@receiver(post_save, sender=Tantara)
def remove_replaced_cover(sender, instance, **kwargs):
    old = getattr(instance, "_old_cover_name", None)
    new = instance.image_cover.name if instance.image_cover else None
    if old and old != new:
        _delete_on_commit(instance.image_cover, old)


@receiver(post_delete, sender=Tantara)
def remove_deleted_story_cover(sender, instance, **kwargs):
    if instance.image_cover:
        _delete_on_commit(instance.image_cover, instance.image_cover.name)
