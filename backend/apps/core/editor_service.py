"""Opérations éditoriales explicites ; aucun ViewSet, routeur ni action implicite."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from helpers.api.exceptions import json_exception_handler
from helpers.api.responses import error

logger = logging.getLogger('safidiko')


def ensure_model_permission(request, model, action):
    """La connexion staff n'accorde jamais à elle seule une permission d'écriture."""
    if not (request.user.is_authenticated and request.user.is_active
            and request.user.is_staff and request.user.has_perm(
                f'{model._meta.app_label}.{action}_{model._meta.model_name}')):
        raise PermissionDenied('Permission éditoriale insuffisante')


def handle_editor_exception(exc):
    """Convertit toutes les erreurs contrôlées en JSON ; cache les détails internes."""
    if isinstance(exc, DjangoValidationError):
        fields = exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}
        return error(400, 'BAD_REQUEST', 'Requête invalide', fields=fields)
    if isinstance(exc, (ProtectedError, RestrictedError, IntegrityError, FileNotFoundError)):
        return error(409, 'CONFLICT', 'Objet lié ou conflit de contraintes')
    try:
        from apps.publication.services import ReleaseNotFound
        if isinstance(exc, ReleaseNotFound):
            return error(409, 'CONFLICT', 'Publication ou fichier indisponible')
    except ImportError:
        pass
    if isinstance(exc, (APIException, Http404)):
        response = json_exception_handler(exc, {})
        if response is not None:
            return response
    logger.exception('Erreur inattendue dans une opération éditoriale', exc_info=(type(exc), exc, exc.__traceback__))
    return error(500, 'INTERNAL_ERROR', 'Erreur interne du serveur')


def _queryset(model, queryset=None):
    return queryset if queryset is not None else model.objects.all()


def editor_list(request, model, serializer, *, search_fields=(), queryset=None):
    ensure_model_permission(request, model, 'view')
    qs = _queryset(model, queryset)
    query = request.query_params.get('search', '').strip()
    if query and search_fields:
        filters = Q()
        for field in search_fields:
            filters |= Q(**{f'{field}__icontains': query})
        qs = qs.filter(filters)
    order = request.query_params.get('ordering', '-created_at')
    if order not in {'created_at', '-created_at', 'updated_at', '-updated_at'}:
        raise ValidationError({'ordering': ['Tri non autorisé.']})
    qs = qs.order_by(order, 'pk')
    paginator = PageNumberPagination()
    paginator.page_size = 25
    page = paginator.paginate_queryset(qs, request)
    results = serializer(page, many=True, context={'request': request}).data
    return paginator.get_paginated_response(results)


def editor_detail(request, model, serializer, pk, *, queryset=None):
    ensure_model_permission(request, model, 'view')
    instance = get_object_or_404(_queryset(model, queryset), pk=pk)
    return Response(serializer(instance, context={'request': request}).data)


def editor_create(request, model, serializer):
    ensure_model_permission(request, model, 'add')
    validated = serializer(data=request.data, context={'request': request})
    validated.is_valid(raise_exception=True)
    with transaction.atomic():
        instance = validated.save()
    return Response(serializer(instance, context={'request': request}).data, status=201)


def editor_update(request, model, serializer, pk, *, partial=False):
    ensure_model_permission(request, model, 'change')
    instance = get_object_or_404(model.objects.all(), pk=pk)
    validated = serializer(instance, data=request.data, partial=partial, context={'request': request})
    validated.is_valid(raise_exception=True)
    with transaction.atomic():
        instance = validated.save()
    return Response(serializer(instance, context={'request': request}).data, status=200)


def editor_delete(request, model, pk):
    ensure_model_permission(request, model, 'delete')
    instance = get_object_or_404(model.objects.all(), pk=pk)
    with transaction.atomic():
        instance.delete()
    # Pas de corps JSON avec un 204 : 200 explicite pour respecter le contrat JSON.
    return Response({'deleted': True}, status=200)
