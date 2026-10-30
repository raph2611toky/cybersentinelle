from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

api_info = openapi.Info(
    title="SAFIDIKO — API publique et éditoriale",
    default_version="v1",
    description="Lecture publique /api/v1/. CRUD staff /api/editor/ avec permissions par modèle. Connexion via /admin/login/. Pour les écritures : cookie sessionid et en-tête X-CSRFToken obtenu via GET /api/session/. Session visiteur sans parcours ni score.",
)
schema_view = get_schema_view(api_info, public=True, permission_classes=(AllowAny,))
ERROR = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["error"],
    properties={
        "error": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["code", "message"],
            properties={
                "code": openapi.Schema(type=openapi.TYPE_STRING),
                "message": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    },
)
ERROR_RESPONSES = {
    400: openapi.Response("Requête invalide", ERROR),
    404: openapi.Response("Ressource introuvable", ERROR),
    405: openapi.Response("Méthode interdite", ERROR),
    500: openapi.Response("Erreur interne", ERROR),
}
