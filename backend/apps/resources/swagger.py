from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from helpers.api.swagger import ERROR_RESPONSES
from apps.content_api.swagger import lang

r = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=[
        "id",
        "title",
        "description",
        "action",
        "audience",
        "kind",
        "href",
        "source",
        "sourceUrl",
        "verifiedAt",
        "reviewerRole",
        "status",
    ],
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING),
        "title": lang,
        "description": lang,
        "action": lang,
        "audience": lang,
        "kind": openapi.Schema(
            type=openapi.TYPE_STRING, enum=["call", "external", "internal"]
        ),
        "href": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
        "source": lang,
        "sourceUrl": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
        "verifiedAt": openapi.Schema(
            type=openapi.TYPE_STRING, format="date", x_nullable=True
        ),
        "reviewerRole": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
        "status": openapi.Schema(
            type=openapi.TYPE_STRING, enum=["active", "unavailable", "review_needed"]
        ),
    },
)
resources_doc = swagger_auto_schema(
    tags=["Ressources"],
    operation_summary="Annuaire vérifié",
    responses={
        200: openapi.Response(
            "Ressources publiques", openapi.Schema(type=openapi.TYPE_ARRAY, items=r)
        ),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)

# Documentation des vues éditoriales (indépendante de views.py).
from apps.core.editor_swagger import editor_swagger_docs, visual_form_parameters
from .serializers import SourceEditorSerializer, RessourceAideEditorSerializer

source_docs = editor_swagger_docs("Source", SourceEditorSerializer)

ressourceaide_docs = editor_swagger_docs("RessourceAide", RessourceAideEditorSerializer)
