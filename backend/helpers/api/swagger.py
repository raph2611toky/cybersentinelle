from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

api_info = openapi.Info(
    title="SAFIDIKO — API publique et éditoriale",
    default_version="v1",
    description="Lecture publique /api/v1/. CRUD staff /api/editor/ avec permissions par modèle. Swagger protégé par un mot de passe dédié ; les opérations d’édition exigent séparément une session Django staff et X-CSRFToken. Les visiteurs ne disposent d’aucune session applicative.",
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
                "fields": openapi.Schema(type=openapi.TYPE_OBJECT, description="Détail des erreurs de champs (tableau de messages ou structure imbriquée selon le serializer)"),
            },
        )
    },
)
ERROR_RESPONSES = {
    401: openapi.Response("Authentification requise", ERROR),
    403: openapi.Response("Accès refusé", ERROR),
    409: openapi.Response("Conflit", ERROR),
    415: openapi.Response("Type de contenu non supporté", ERROR),
    400: openapi.Response("Requête invalide", ERROR),
    404: openapi.Response("Ressource introuvable", ERROR),
    405: openapi.Response("Méthode interdite", ERROR),
    500: openapi.Response("Erreur interne", ERROR),
}
