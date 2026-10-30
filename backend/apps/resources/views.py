from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from config.responses import public_json, error, failed
from apps.publication.services import read_content, ReleaseNotFound
from .swagger import resources_doc
from apps.core.views import EditorialViewSet
from .models import Source, RessourceAide
from .serializers import SourceEditorSerializer, RessourceAideEditorSerializer


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


class SourceViewSet(EditorialViewSet):
    search_fields = ["code", "nom_fr", "nom_mg"]
    queryset = Source.objects.all()
    serializer_class = SourceEditorSerializer


class RessourceAideViewSet(EditorialViewSet):
    search_fields = ["cle", "titre_fr", "titre_mg"]
    queryset = RessourceAide.objects.all().select_related("source", "ressource_repli")
    serializer_class = RessourceAideEditorSerializer
