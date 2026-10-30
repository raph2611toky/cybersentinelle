from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from helpers.api.swagger import ERROR_RESPONSES

file_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["path", "type", "sha256", "bytes", "language"],
    properties={
        "path": openapi.Schema(type=openapi.TYPE_STRING),
        "type": openapi.Schema(
            type=openapi.TYPE_STRING, enum=["STORY", "QUESTIONS", "RESOURCES", "MEDIA"]
        ),
        "sha256": openapi.Schema(type=openapi.TYPE_STRING),
        "bytes": openapi.Schema(type=openapi.TYPE_INTEGER),
        "language": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
    },
)
version_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["version", "date", "languages", "sha256", "files"],
    properties={
        "version": openapi.Schema(type=openapi.TYPE_STRING),
        "date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
        "languages": openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)
        ),
        "sha256": openapi.Schema(type=openapi.TYPE_STRING),
        "files": openapi.Schema(type=openapi.TYPE_ARRAY, items=file_schema),
    },
)
version_doc = swagger_auto_schema(
    tags=["Publication"],
    operation_summary="Version active",
    responses={
        200: openapi.Response("Manifeste public", version_schema),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)

# Swagger de l'édition des versions : cinq APIView indépendantes.
from drf_yasg.utils import swagger_auto_schema
from apps.publication.serializers import ReleaseEditorSerializer, PublishSerializer
from apps.core.editor_swagger import editor_swagger_docs

_release_docs = editor_swagger_docs('Publication', ReleaseEditorSerializer)
release_list_doc = _release_docs['list']
release_detail_doc = _release_docs['retrieve']
release_publish_doc = swagger_auto_schema(
    tags=['Edition - Publication'], operation_summary='Publier une nouvelle version',
    request_body=PublishSerializer,
    responses={201: openapi.Response('Publication créée', ReleaseEditorSerializer),
               **{c: r for c, r in ERROR_RESPONSES.items() if c in (400, 401, 403, 405, 409, 415, 500)}},
)
release_rollback_doc = swagger_auto_schema(
    tags=['Edition - Publication'], operation_summary='Restaurer une version existante',
    responses={200: openapi.Response('Version réactivée', ReleaseEditorSerializer),
               **{c: r for c, r in ERROR_RESPONSES.items() if c in (400, 401, 403, 404, 405, 409, 415, 500)}},
)
validation_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT, required=['valid', 'files', 'visuals'],
    properties={'valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'files': openapi.Schema(type=openapi.TYPE_INTEGER),
                'visuals': openapi.Schema(type=openapi.TYPE_INTEGER)})
release_validate_doc = swagger_auto_schema(
    tags=['Edition - Publication'], operation_summary='Valider les contenus publiables',
    responses={200: openapi.Response('Validation terminée', validation_schema),
               **{c: r for c, r in ERROR_RESPONSES.items() if c in (400, 401, 403, 405, 409, 415, 500)}},
)
