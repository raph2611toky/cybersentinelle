"""API publique des versions SAFIDIKO ; lecture seule."""
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from helpers.api.responses import public_json, error, failed
from .services import active_release, ReleaseNotFound, manifest_public
from .swagger import version_doc


class ContentVersionView(APIView):
    permission_classes = [AllowAny]

    @version_doc
    def get(self, request):
        try:
            _, manifest = active_release()
            return public_json(request, manifest_public(manifest), max_age=30)
        except ReleaseNotFound:
            return error(503, "CONTENT_NOT_PUBLISHED", "Contenu public indisponible")
        except Exception as exc:
            return failed(exc)


