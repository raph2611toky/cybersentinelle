"""Consultation et activation des releases : une méthode par classe APIView."""

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.editor_service import ensure_model_permission, handle_editor_exception
from .models import VersionContenu
from .serializers import ReleaseEditorSerializer, PublishSerializer
from .services import publish, rollback, publication_payload, ReleaseNotFound
from .swagger import (release_list_doc, release_detail_doc, release_publish_doc,
                      release_rollback_doc, release_validate_doc)


class ReleaseListView(APIView):
    permission_classes = [IsAdminUser]

    @release_list_doc
    def get(self, request):
        try:
            ensure_model_permission(request, VersionContenu, 'view')
            versions = VersionContenu.objects.prefetch_related('fichiers').order_by('-created_at')
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            paginator.page_size = 25
            page = paginator.paginate_queryset(versions, request)
            return paginator.get_paginated_response(
                ReleaseEditorSerializer(page, many=True, context={'request': request}).data)
        except Exception as exc:
            return handle_editor_exception(exc)


class ReleaseDetailView(APIView):
    permission_classes = [IsAdminUser]

    @release_detail_doc
    def get(self, request, pk):
        try:
            ensure_model_permission(request, VersionContenu, 'view')
            version = get_object_or_404(VersionContenu.objects.prefetch_related('fichiers'), pk=pk)
            return Response(ReleaseEditorSerializer(version, context={'request': request}).data)
        except Exception as exc:
            return handle_editor_exception(exc)


class ReleasePublishView(APIView):
    permission_classes = [IsAdminUser]

    @release_publish_doc
    def post(self, request):
        try:
            ensure_model_permission(request, VersionContenu, 'add')
            data = PublishSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            version = publish(**data.validated_data)
            return Response(ReleaseEditorSerializer(version, context={'request': request}).data, status=201)
        except Exception as exc:
            return handle_editor_exception(exc)


class ReleaseRollbackView(APIView):
    permission_classes = [IsAdminUser]

    @release_rollback_doc
    def post(self, request, pk):
        try:
            ensure_model_permission(request, VersionContenu, 'change')
            version = get_object_or_404(VersionContenu, pk=pk)
            activated = rollback(version.numero)
            return Response(ReleaseEditorSerializer(activated, context={'request': request}).data)
        except Exception as exc:
            return handle_editor_exception(exc)


class ReleaseValidateView(APIView):
    permission_classes = [IsAdminUser]

    @release_validate_doc
    def get(self, request):
        try:
            ensure_model_permission(request, VersionContenu, 'view')
            payload, assets = publication_payload()
            return Response({'valid': True, 'files': len(payload), 'visuals': len(assets)})
        except Exception as exc:
            return handle_editor_exception(exc)
