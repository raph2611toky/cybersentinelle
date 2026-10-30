from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from config.responses import public_json, error, failed
from .services import active_release, ReleaseNotFound, manifest_public
from .swagger import version_doc
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.core.permissions import EditorialPermissions
from apps.core.views import Conflict
from .models import VersionContenu
from .serializers import ReleaseEditorSerializer, PublishSerializer
from .services import publish, rollback, publication_payload


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


class ReleaseViewSet(viewsets.ReadOnlyModelViewSet):
    """Releases immuables : publier et restaurer via les services de validation."""

    queryset = VersionContenu.objects.prefetch_related("fichiers").all()
    serializer_class = ReleaseEditorSerializer
    permission_classes = [EditorialPermissions]

    def require_permission(self, codename):
        if not self.request.user.has_perm("publication." + codename):
            raise PermissionDenied()

    def run_service(self, operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        except IntegrityError as exc:
            raise Conflict() from exc
        except (FileNotFoundError, ReleaseNotFound) as exc:
            raise Conflict("Fichiers de publication indisponibles.") from exc

    @swagger_auto_schema(
        request_body=PublishSerializer, responses={201: ReleaseEditorSerializer}
    )
    @action(detail=False, methods=["post"])
    def publish(self, request):
        self.require_permission("add_versioncontenu")
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        release = self.run_service(publish, **serializer.validated_data)
        return Response(ReleaseEditorSerializer(release).data, status=201)

    @action(detail=True, methods=["post"])
    def rollback(self, request, pk=None):
        self.require_permission("change_versioncontenu")
        release = self.get_object()
        release = self.run_service(rollback, release.numero)
        return Response(ReleaseEditorSerializer(release).data)

    @action(detail=False, methods=["get"])
    def validate(self, request):
        payload, assets = self.run_service(publication_payload)
        return Response({"valid": True, "files": len(payload), "visuals": len(assets)})
