from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from helpers.api.responses import public_json, error, failed
from apps.publication.services import read_content, ReleaseNotFound
from .swagger import resources_doc


class ResourcesListView(APIView):
    permission_classes = [AllowAny]

    @resources_doc
    def get(self, request):
        try:
            data, _ = read_content("resources.json")
            return public_json(request, data)
        except ReleaseNotFound:
            return error(503, "CONTENT_NOT_PUBLISHED", "Contenu public indisponible")
        except Exception as exc:
            return failed(exc)
