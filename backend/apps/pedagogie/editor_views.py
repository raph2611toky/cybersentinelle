"""Edition staff : une APIView explicite par méthode HTTP, aucun ViewSet."""

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from apps.core.editor_service import (editor_list, editor_detail, editor_create, editor_update, editor_delete, handle_editor_exception)
from .models import QuestionPedagogique
from .serializers import QuestionPedagogiqueEditorSerializer
from .swagger import questionpedagogique_docs


class QuestionPedagogiqueListView(APIView):
    permission_classes = [IsAdminUser]

    @questionpedagogique_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, QuestionPedagogique, QuestionPedagogiqueEditorSerializer, search_fields=('cle', 'question_fr', 'question_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class QuestionPedagogiqueDetailView(APIView):
    permission_classes = [IsAdminUser]

    @questionpedagogique_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, QuestionPedagogique, QuestionPedagogiqueEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class QuestionPedagogiqueCreateView(APIView):
    permission_classes = [IsAdminUser]

    @questionpedagogique_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, QuestionPedagogique, QuestionPedagogiqueEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class QuestionPedagogiqueUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @questionpedagogique_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, QuestionPedagogique, QuestionPedagogiqueEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class QuestionPedagogiquePartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @questionpedagogique_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, QuestionPedagogique, QuestionPedagogiqueEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class QuestionPedagogiqueDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @questionpedagogique_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, QuestionPedagogique, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


