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
from .swagger import story_list_doc, story_detail_doc, published_cover_doc


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


class PublishedStoryCoverAPIView(APIView):
    """Retourne une couverture PNG uniquement depuis une release publiée vérifiée."""
    permission_classes = [AllowAny]
    authentication_classes = []

    @published_cover_doc
    def get(self, request, version, slug):
        try:
            import re
            import json
            import hashlib
            from django.http import FileResponse
            from apps.publication.models import VersionContenu
            from apps.publication.services import _safe_release_dir, sha
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}", version):
                return error(404, "NOT_FOUND", "Couverture introuvable")
            release = VersionContenu.objects.filter(numero=version).first()
            if not release:
                return error(404, "NOT_FOUND", "Couverture introuvable")
            root = _safe_release_dir(release.repertoire_snapshot)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            entries = manifest.get("files", [])
            canonical = "\n".join(f"{e['path']}:{e['sha256']}" for e in sorted(entries, key=lambda e: e["path"]))
            if manifest.get("version") != release.numero or sha(canonical.encode("utf-8")) != release.digest_global:
                return error(503, "CONTENT_NOT_PUBLISHED", "Publication invalide")
            relative = f"covers/{slug}.png"
            entry = next((e for e in entries if e.get("path") == relative and e.get("type") == "MEDIA"), None)
            if entry is None:
                return error(404, "NOT_FOUND", "Couverture introuvable")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                return error(404, "NOT_FOUND", "Couverture introuvable")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != entry["sha256"]:
                return error(503, "CONTENT_NOT_PUBLISHED", "Couverture publiée corrompue")
            response = FileResponse(path.open("rb"), content_type="image/png")
            response["Cache-Control"] = "public, max-age=86400, immutable"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception as exc:
            return failed(exc)
