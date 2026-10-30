"""Une seule méthode métier (GET) par APIView ; HEAD/OPTIONS héritées de DRF."""

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from helpers.api.responses import public_json, error, failed
from apps.publication.services import (
    read_content,
    ReleaseNotFound,
    decorate_story_urls,
    active_release,
)
from .swagger import story_list_doc, story_detail_doc


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
