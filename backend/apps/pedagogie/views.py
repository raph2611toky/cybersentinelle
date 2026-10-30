from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from config.responses import public_json, error, failed
from apps.publication.services import read_content, ReleaseNotFound
from .swagger import questions_doc
from apps.core.views import EditorialViewSet
from .models import QuestionPedagogique
from .serializers import QuestionPedagogiqueEditorSerializer


class QuestionsListView(APIView):
    permission_classes = [AllowAny]

    @questions_doc
    def get(self, request):
        try:
            data, _ = read_content("questions.json")
            return public_json(request, data)
        except ReleaseNotFound:
            return error(503, "CONTENT_NOT_PUBLISHED", "Contenu public indisponible")
        except Exception as exc:
            return failed(exc)


class QuestionPedagogiqueViewSet(EditorialViewSet):
    search_fields = ["cle", "question_fr", "question_mg"]
    queryset = (
        QuestionPedagogique.objects.all()
        .select_related("sujet")
        .prefetch_related("ressources_liees")
    )
    serializer_class = QuestionPedagogiqueEditorSerializer
