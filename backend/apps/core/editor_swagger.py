"""Schémas communs des APIView éditoriales, importés depuis les swagger.py des apps."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from helpers.api.swagger import ERROR_RESPONSES


def editor_swagger_docs(label, serializer_class, *, multipart=False, manual_parameters=None, partial_parameters=None):
    """Chaque décorateur correspond à une vue distincte et à un code HTTP exact."""
    page_serializer = type(
        f'{label.replace(" ", "")}PageSerializer', (serializers.Serializer,), {
            'count': serializers.IntegerField(),
            'next': serializers.URLField(allow_null=True),
            'previous': serializers.URLField(allow_null=True),
            'results': serializer_class(many=True),
        }
    )
    deleted = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['deleted'],
        properties={'deleted': openapi.Schema(type=openapi.TYPE_BOOLEAN)},
    )
    search = [
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                          enum=['created_at', '-created_at', 'updated_at', '-updated_at']),
        openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False),
    ]
    shared = {code: response for code, response in ERROR_RESPONSES.items()
              if code in (400, 401, 403, 404, 405, 409, 415, 500)}
    def decorate(operation, response_status, response_schema, *, request_schema=None, extra=None):
        kwargs = dict(tags=[f'Edition - {label}'], operation_summary=f'{operation} : {label}',
                      responses={response_status: openapi.Response(operation, response_schema), **shared})
        if extra:
            kwargs['manual_parameters'] = extra
        if request_schema is not None:
            kwargs['request_body'] = request_schema
        return swagger_auto_schema(**kwargs)
    # Les uploads utilisent exclusivement des paramètres formData manuels, jamais request_body.
    input_schema = None if multipart else serializer_class
    form_params = manual_parameters if multipart else None
    return {
        'list': decorate('Liste', 200, page_serializer, extra=search),
        'retrieve': decorate('Détail', 200, serializer_class),
        'create': decorate('Création', 201, serializer_class, request_schema=input_schema, extra=form_params),
        'update': decorate('Mise à jour complète', 200, serializer_class, request_schema=input_schema, extra=form_params),
        'partial': decorate('Mise à jour partielle', 200, serializer_class, request_schema=input_schema, extra=(partial_parameters if partial_parameters is not None else visual_form_parameters(required_fields=False)) if multipart else None),
        'delete': decorate('Suppression', 200, deleted),
    }


def visual_form_parameters(*, required_fields=True):
    """Paramètres multipart explicites et typés ; le champ fichier est un vrai upload formData."""
    fields = [
        ('code', 'string'), ('type', 'string'), ('fichier', 'file'), ('chemin_asset', 'string'),
        ('format', 'string'), ('largeur_px', 'integer'), ('hauteur_px', 'integer'),
        ('alt_fr', 'string'), ('alt_mg', 'string'), ('decoratif', 'boolean'),
        ('licence', 'string'), ('url_provenance', 'string'), ('attribution', 'string'),
        ('sha256', 'string'), ('actif', 'boolean'),
    ]
    mandatory = {'code', 'type', 'format', 'licence'} if required_fields else set()
    return [openapi.Parameter(name, openapi.IN_FORM, type=kind, required=name in mandatory,
                               description=('Fichier ou chemin_asset requis ; autres contraintes validées côté serveur.'
                                            if name in {'fichier', 'chemin_asset'}
                                            else 'Champ du formulaire multipart Visuel'))
            for name, kind in fields]
