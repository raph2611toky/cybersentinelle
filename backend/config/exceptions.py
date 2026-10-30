from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
    ParseError,
    MethodNotAllowed,
)


def json_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, NotFound):
        code = "NOT_FOUND"
    elif isinstance(exc, MethodNotAllowed):
        code = "METHOD_NOT_ALLOWED"
    elif isinstance(exc, (ValidationError, ParseError)):
        code = "BAD_REQUEST"
    elif isinstance(exc, PermissionDenied):
        code = "FORBIDDEN"
    else:
        code = "HTTP_ERROR"
    # Ne jamais exposer de détails internes ou de données sensibles.
    messages = {
        "NOT_FOUND": "Ressource introuvable",
        "METHOD_NOT_ALLOWED": "Méthode interdite",
        "BAD_REQUEST": "Requête invalide",
        "FORBIDDEN": "Accès refusé",
        "HTTP_ERROR": "Erreur de requête",
    }
    details = response.data
    response.data = {"error": {"code": code, "message": messages[code]}}
    if isinstance(exc, ValidationError):
        response.data["error"]["fields"] = details
    if response.status_code == 409:
        response.data["error"] = {
            "code": "CONFLICT",
            "message": "Objet lié ou conflit de contraintes.",
        }
    return response
