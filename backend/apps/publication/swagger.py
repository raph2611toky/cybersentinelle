from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from config.swagger import ERROR_RESPONSES

file_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["path", "type", "sha256", "bytes", "language"],
    properties={
        "path": openapi.Schema(type=openapi.TYPE_STRING),
        "type": openapi.Schema(
            type=openapi.TYPE_STRING, enum=["STORY", "QUESTIONS", "RESOURCES"]
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
