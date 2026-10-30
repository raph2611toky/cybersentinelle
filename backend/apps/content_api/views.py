"""Une seule méthode métier (GET) par APIView ; HEAD/OPTIONS héritées de DRF."""

from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from config.responses import public_json, error, failed
from apps.publication.services import (
    read_content,
    ReleaseNotFound,
    decorate_story_urls,
    active_release,
)
from .swagger import story_list_doc, story_detail_doc
from apps.core.views import EditorialViewSet
from .models import Sujet, Visuel, Tantara, Noeud, OptionDecision
from .serializers import (
    SujetEditorSerializer,
    VisuelEditorSerializer,
    TantaraEditorSerializer,
    NoeudEditorSerializer,
    OptionDecisionEditorSerializer,
)


class StoriesListView(APIView):
    permission_classes = [AllowAny]

    @story_list_doc
    def get(self, request):
        try:
            _, manifest = active_release()
            data = []
            for entry in manifest["files"]:
                if entry["type"] != "STORY":
                    continue
                item, _ = read_content(entry["path"])
                item.pop("nodes", None)
                decorate_story_urls(item, manifest, request)
                data.append(item)
            return public_json(request, data)
        except ReleaseNotFound:
            return error(503, "CONTENT_NOT_PUBLISHED", "Contenu public indisponible")
        except Exception as exc:
            return failed(exc)


class StoryDetailView(APIView):
    permission_classes = [AllowAny]

    @story_detail_doc
    def get(self, request, slug):
        try:
            _, manifest = active_release()
            if not any(
                entry["path"] == f"stories/{slug}.json" for entry in manifest["files"]
            ):
                return error(404, "NOT_FOUND", "Ressource introuvable")
            data, manifest = read_content(f"stories/{slug}.json")
            decorate_story_urls(data, manifest, request)
            return public_json(request, data)
        except ReleaseNotFound:
            return error(503, "CONTENT_NOT_PUBLISHED", "Contenu public indisponible")
        except Exception as exc:
            return failed(exc)


class SujetViewSet(EditorialViewSet):
    search_fields = ["code", "libelle_fr", "libelle_mg"]
    queryset = Sujet.objects.all()
    serializer_class = SujetEditorSerializer


class VisuelViewSet(EditorialViewSet):
    search_fields = ["code", "alt_fr", "alt_mg"]
    queryset = Visuel.objects.all()
    serializer_class = VisuelEditorSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class TantaraViewSet(EditorialViewSet):
    search_fields = ["slug", "titre_fr", "titre_mg"]
    queryset = (
        Tantara.objects.all().select_related("visuel_heros").prefetch_related("sujets")
    )
    serializer_class = TantaraEditorSerializer


class NoeudViewSet(EditorialViewSet):
    search_fields = ["cle", "titre_fr", "tantara__slug"]
    queryset = Noeud.objects.all().select_related("tantara", "visuel", "noeud_suivant")
    serializer_class = NoeudEditorSerializer


class OptionDecisionViewSet(EditorialViewSet):
    search_fields = ["cle", "label_fr", "noeud__tantara__slug"]
    queryset = OptionDecision.objects.all().select_related("noeud", "noeud_cible")
    serializer_class = OptionDecisionEditorSerializer
