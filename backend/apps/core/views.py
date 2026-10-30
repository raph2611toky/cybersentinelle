"""Edition staff : une APIView explicite par méthode HTTP, aucun ViewSet."""

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from apps.core.editor_service import (editor_list, editor_detail, editor_create, editor_update, editor_delete, handle_editor_exception)
from .models import Langue
from .serializers import LangueEditorSerializer
from .swagger import langue_docs


class LangueListView(APIView):
    permission_classes = [IsAdminUser]

    @langue_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, Langue, LangueEditorSerializer, search_fields=('code', 'nom_fr', 'nom_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class LangueDetailView(APIView):
    permission_classes = [IsAdminUser]

    @langue_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, Langue, LangueEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class LangueCreateView(APIView):
    permission_classes = [IsAdminUser]

    @langue_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, Langue, LangueEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class LangueUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @langue_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, Langue, LangueEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class LanguePartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @langue_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, Langue, LangueEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class LangueDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @langue_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, Langue, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


