"""Edition staff : une APIView explicite par méthode HTTP, aucun ViewSet."""

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from apps.core.editor_service import (editor_list, editor_detail, editor_create, editor_update, editor_delete, handle_editor_exception)
from .models import Source, RessourceAide
from .serializers import SourceEditorSerializer, RessourceAideEditorSerializer
from .swagger import source_docs, ressourceaide_docs


class SourceListView(APIView):
    permission_classes = [IsAdminUser]

    @source_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, Source, SourceEditorSerializer, search_fields=('code', 'nom_fr', 'nom_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class SourceDetailView(APIView):
    permission_classes = [IsAdminUser]

    @source_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, Source, SourceEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class SourceCreateView(APIView):
    permission_classes = [IsAdminUser]

    @source_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, Source, SourceEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class SourceUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @source_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, Source, SourceEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class SourcePartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @source_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, Source, SourceEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class SourceDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @source_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, Source, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class RessourceAideListView(APIView):
    permission_classes = [IsAdminUser]

    @ressourceaide_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, RessourceAide, RessourceAideEditorSerializer, search_fields=('cle', 'titre_fr', 'titre_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class RessourceAideDetailView(APIView):
    permission_classes = [IsAdminUser]

    @ressourceaide_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, RessourceAide, RessourceAideEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class RessourceAideCreateView(APIView):
    permission_classes = [IsAdminUser]

    @ressourceaide_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, RessourceAide, RessourceAideEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class RessourceAideUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @ressourceaide_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, RessourceAide, RessourceAideEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class RessourceAidePartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @ressourceaide_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, RessourceAide, RessourceAideEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class RessourceAideDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @ressourceaide_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, RessourceAide, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


