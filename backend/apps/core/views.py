from rest_framework.permissions import AllowAny
from datetime import datetime, timedelta
from django.db import transaction, IntegrityError
from django.db.models.deletion import ProtectedError, RestrictedError
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status, viewsets, filters
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from helpers.helper import time_elapsed
from .models import Langue
from .permissions import EditorialPermissions
from .serializers import LangueEditorSerializer, SessionSerializer


class Conflict(APIException):
    status_code = 409
    default_detail = (
        "Opération incompatible avec les relations ou les contraintes existantes."
    )
    default_code = "conflict"


class EditorialViewSet(viewsets.ModelViewSet):
    permission_classes = [EditorialPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    lookup_value_regex = "[0-9a-f-]{36}"

    def perform_create(self, serializer):
        self.save_validated(serializer)

    def perform_update(self, serializer):
        self.save_validated(serializer)

    def save_validated(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise Conflict() from exc

    def perform_destroy(self, instance):
        try:
            with transaction.atomic():
                instance.delete()
        except (ProtectedError, RestrictedError, IntegrityError) as exc:
            raise Conflict() from exc


class LangueViewSet(EditorialViewSet):
    queryset = Langue.objects.all()
    serializer_class = LangueEditorSerializer


@method_decorator(csrf_protect, name="dispatch")
class VisitorSessionView(APIView):
    """Session technique pseudonyme. Aucun parcours, score ou témoignage enregistré."""

    permission_classes = [AllowAny]

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "session"

    def payload(self, request):
        started = request.session.get("visitor_started_at")
        if not started:
            return {"active": False, "language": "fr"}
        return {
            "active": True,
            "language": request.session.get("visitor_language", "fr"),
            "expires_at": request.session.get_expiry_date(),
            "elapsed_seconds": time_elapsed(datetime.fromisoformat(started)),
        }

    @swagger_auto_schema(responses={200: SessionSerializer})
    def get(self, request):
        get_token(request)
        return Response(self.payload(request))

    @swagger_auto_schema(
        request_body=SessionSerializer, responses={201: SessionSerializer}
    )
    def post(self, request):
        serializer = SessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.session.cycle_key()
        request.session["visitor_started_at"] = timezone.now().isoformat()
        request.session["visitor_language"] = serializer.validated_data.get(
            "language", "fr"
        )
        request.session.set_expiry(timezone.now() + timedelta(days=1))
        return Response(self.payload(request), status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=SessionSerializer, responses={200: SessionSerializer}
    )
    def patch(self, request):
        if not request.session.get("visitor_started_at"):
            return Response(
                {"detail": "Créer une session avant de la modifier."}, status=404
            )
        serializer = SessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "language" in serializer.validated_data:
            request.session["visitor_language"] = serializer.validated_data["language"]
        return Response(self.payload(request))

    @swagger_auto_schema(responses={204: "Session visiteur effacée"})
    def delete(self, request):
        if request.user.is_authenticated:
            request.session.pop("visitor_started_at", None)
            request.session.pop("visitor_language", None)
            request.session.cycle_key()
        else:
            request.session.flush()
        return Response(status=204)
