"""Durable, auditable jobs for French -> Malagasy editorial translation.

The source copy is fictional editorial content, never a user or victim message.
"""
import hashlib
from django.db import models
from apps.core.models import ModeleBase


class TranslationJob(ModeleBase):
    class State(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        RUNNING = 'RUNNING', 'En cours'
        DONE = 'DONE', 'Traduction à relire'
        FAILED = 'FAILED', 'Erreur'
        STALE = 'STALE', 'Remplacée'

    target_type = models.CharField(max_length=80, db_index=True)
    target_id = models.CharField(max_length=50, db_index=True)
    # For direct models: ["titre_fr"]; for a draft graph: ["nodes", id, "title"] etc.
    path = models.JSONField()
    source_text = models.TextField()
    source_sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = 'translation_job'
        indexes = [models.Index(fields=['target_type', 'target_id', 'state'])]
        ordering = ['-created_at']

    @staticmethod
    def fingerprint(text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
