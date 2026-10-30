from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from config.responses import public_json, error, failed
from apps.publication.services import read_content, ReleaseNotFound
from .swagger import questions_doc


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
