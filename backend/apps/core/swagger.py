"""Swagger explicite pour les opérations Langue."""
from apps.core.editor_swagger import editor_swagger_docs
from .serializers import LangueEditorSerializer

langue_docs = editor_swagger_docs("Langue", LangueEditorSerializer)
