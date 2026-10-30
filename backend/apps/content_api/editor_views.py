"""Edition staff : une APIView explicite par méthode HTTP, aucun ViewSet."""

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from apps.core.editor_service import (editor_list, editor_detail, editor_create, editor_update, editor_delete, handle_editor_exception)
from .models import Sujet, Visuel, Tantara, Noeud, OptionDecision
from .serializers import SujetEditorSerializer, VisuelEditorSerializer, TantaraEditorSerializer, NoeudEditorSerializer, OptionDecisionEditorSerializer
from .swagger import sujet_docs, visuel_docs, tantara_docs, noeud_docs, optiondecision_docs


class SujetListView(APIView):
    permission_classes = [IsAdminUser]

    @sujet_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, Sujet, SujetEditorSerializer, search_fields=('code', 'libelle_fr', 'libelle_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class SujetDetailView(APIView):
    permission_classes = [IsAdminUser]

    @sujet_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, Sujet, SujetEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class SujetCreateView(APIView):
    permission_classes = [IsAdminUser]

    @sujet_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, Sujet, SujetEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class SujetUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @sujet_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, Sujet, SujetEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class SujetPartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @sujet_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, Sujet, SujetEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class SujetDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @sujet_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, Sujet, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class VisuelListView(APIView):
    permission_classes = [IsAdminUser]

    @visuel_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, Visuel, VisuelEditorSerializer, search_fields=('code', 'alt_fr', 'alt_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class VisuelDetailView(APIView):
    permission_classes = [IsAdminUser]

    @visuel_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, Visuel, VisuelEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class VisuelCreateView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @visuel_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, Visuel, VisuelEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class VisuelUpdateView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @visuel_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, Visuel, VisuelEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class VisuelPartialUpdateView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @visuel_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, Visuel, VisuelEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class VisuelDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @visuel_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, Visuel, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class TantaraListView(APIView):
    permission_classes = [IsAdminUser]

    @tantara_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, Tantara, TantaraEditorSerializer, search_fields=('slug', 'titre_fr', 'titre_mg'))
        except Exception as exc:
            return handle_editor_exception(exc)


class TantaraDetailView(APIView):
    permission_classes = [IsAdminUser]

    @tantara_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, Tantara, TantaraEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class TantaraCreateView(APIView):
    permission_classes = [IsAdminUser]

    @tantara_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, Tantara, TantaraEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class TantaraUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @tantara_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, Tantara, TantaraEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class TantaraPartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @tantara_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, Tantara, TantaraEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class TantaraDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @tantara_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, Tantara, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class NoeudListView(APIView):
    permission_classes = [IsAdminUser]

    @noeud_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, Noeud, NoeudEditorSerializer, search_fields=('cle', 'titre_fr', 'tantara__slug'))
        except Exception as exc:
            return handle_editor_exception(exc)


class NoeudDetailView(APIView):
    permission_classes = [IsAdminUser]

    @noeud_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, Noeud, NoeudEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class NoeudCreateView(APIView):
    permission_classes = [IsAdminUser]

    @noeud_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, Noeud, NoeudEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class NoeudUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @noeud_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, Noeud, NoeudEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class NoeudPartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @noeud_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, Noeud, NoeudEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class NoeudDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @noeud_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, Noeud, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class OptionDecisionListView(APIView):
    permission_classes = [IsAdminUser]

    @optiondecision_docs["list"]
    def get(self, request):
        try:
            return editor_list(request, OptionDecision, OptionDecisionEditorSerializer, search_fields=('cle', 'label_fr', 'noeud__tantara__slug'))
        except Exception as exc:
            return handle_editor_exception(exc)


class OptionDecisionDetailView(APIView):
    permission_classes = [IsAdminUser]

    @optiondecision_docs["retrieve"]
    def get(self, request, pk):
        try:
            return editor_detail(request, OptionDecision, OptionDecisionEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class OptionDecisionCreateView(APIView):
    permission_classes = [IsAdminUser]

    @optiondecision_docs["create"]
    def post(self, request):
        try:
            return editor_create(request, OptionDecision, OptionDecisionEditorSerializer)
        except Exception as exc:
            return handle_editor_exception(exc)


class OptionDecisionUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @optiondecision_docs["update"]
    def put(self, request, pk):
        try:
            return editor_update(request, OptionDecision, OptionDecisionEditorSerializer, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


class OptionDecisionPartialUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @optiondecision_docs["partial"]
    def patch(self, request, pk):
        try:
            return editor_update(request, OptionDecision, OptionDecisionEditorSerializer, pk, partial=True)
        except Exception as exc:
            return handle_editor_exception(exc)


class OptionDecisionDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @optiondecision_docs["delete"]
    def delete(self, request, pk):
        try:
            return editor_delete(request, OptionDecision, pk)
        except Exception as exc:
            return handle_editor_exception(exc)


