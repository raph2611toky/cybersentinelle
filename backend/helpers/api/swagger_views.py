"""Décorateurs Swagger dédiés aux vues transversales (séparés de config/views.py)."""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from helpers.api.swagger import ERROR_RESPONSES

_ok = openapi.Schema(type=openapi.TYPE_OBJECT, properties={"status": openapi.Schema(type=openapi.TYPE_STRING)})
health_docs = swagger_auto_schema(
    tags=["Système"], operation_summary="Santé de l'API",
    responses={200: openapi.Response("Service disponible", _ok), 500: ERROR_RESPONSES[500]},
)
login_page_docs = swagger_auto_schema(
    tags=["Documentation protégée"], operation_summary="Page HTML d'accès Swagger",
    responses={200: openapi.Response("Page HTML de connexion")},
)
unlock_docs = swagger_auto_schema(
    tags=["Documentation protégée"], operation_summary="Déverrouiller la documentation",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT, required=["password"],
        properties={"password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                    "next": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
    responses={
        200: openapi.Response("Accès accordé", openapi.Schema(
            type=openapi.TYPE_OBJECT, required=["authenticated", "redirect"],
            properties={"authenticated": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "redirect": openapi.Schema(type=openapi.TYPE_STRING)},
        )),
        400: ERROR_RESPONSES[400], 401: ERROR_RESPONSES[401],
        403: ERROR_RESPONSES[403], 500: ERROR_RESPONSES[500],
        503: openapi.Response("Accès Swagger désactivé", ERROR_RESPONSES[500].schema),
    },
)
logout_docs = swagger_auto_schema(
    tags=["Documentation protégée"], operation_summary="Fermer l'accès Swagger",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT),
    responses={200: openapi.Response("Déconnecté", openapi.Schema(
        type=openapi.TYPE_OBJECT, required=["authenticated"],
        properties={"authenticated": openapi.Schema(type=openapi.TYPE_BOOLEAN)},
    )), 500: ERROR_RESPONSES[500]},
)
