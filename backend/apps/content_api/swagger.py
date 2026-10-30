"""Toutes les descriptions drf-yasg sont séparées des classes APIView."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from config.swagger import ERROR_RESPONSES

str_field = lambda description="": openapi.Schema(
    type=openapi.TYPE_STRING, description=description
)
lang = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["fr", "mg"],
    properties={"fr": str_field(), "mg": str_field()},
)
option = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["id", "label", "feedback", "quality", "next"],
    properties={
        "id": str_field(),
        "label": lang,
        "feedback": lang,
        "quality": openapi.Schema(type=openapi.TYPE_NUMBER, minimum=0, maximum=1),
        "next": str_field(),
    },
)
node = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["kind", "title", "text"],
    properties={
        "kind": openapi.Schema(
            type=openapi.TYPE_STRING, enum=["scene", "decision", "ending"]
        ),
        "title": lang,
        "text": lang,
        "tag": str_field("Scène uniquement"),
        "visual": str_field("Identifiant visuel statique"),
        "visual_url": str_field("URL absolue si visuel présent"),
        "next": str_field("Transition scène uniquement"),
        "weight": openapi.Schema(
            type=openapi.TYPE_INTEGER, description="Décision uniquement"
        ),
        "options": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=option,
            description="2 ou 3 options pour une décision",
        ),
    },
)
properties = {
    "id": str_field(),
    "number": str_field(),
    "title": lang,
    "subtitle": lang,
    "theme": lang,
    "description": lang,
    "warning": lang,
    "duration": str_field(),
    "expectedDecisions": openapi.Schema(type=openapi.TYPE_INTEGER),
    "palette": str_field(),
    "heroVisual": str_field(),
    "heroVisual_url": str_field("URL absolue si fichier présent"),
}
required = [
    "id",
    "number",
    "title",
    "subtitle",
    "theme",
    "description",
    "warning",
    "duration",
    "expectedDecisions",
    "palette",
    "heroVisual",
]
story_summary = openapi.Schema(
    type=openapi.TYPE_OBJECT, required=required, properties=properties
)
story_detail = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=required + ["nodes"],
    properties={
        **properties,
        "nodes": openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=node),
    },
)
story_list_doc = swagger_auto_schema(
    tags=["Tantara"],
    operation_summary="Liste des trois Tantara",
    operation_description="GET sans identité, réponses bilingues. HEAD et OPTIONS également supportés.",
    responses={
        200: openapi.Response(
            "Catalogue public",
            openapi.Schema(type=openapi.TYPE_ARRAY, items=story_summary),
        ),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)
story_detail_doc = swagger_auto_schema(
    tags=["Tantara"],
    operation_summary="Graphe narratif complet",
    operation_description="Slug limité à aza-zaraina, tsy-irery et aza-manaiky.",
    responses={
        200: openapi.Response("Récit intégral", story_detail),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)
