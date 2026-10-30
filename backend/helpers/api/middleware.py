import json
from django.http import HttpResponse


class JsonErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/api/"):
            return response
        labels = {
            400: ("BAD_REQUEST", "Requête invalide"),
            401: ("UNAUTHENTICATED", "Authentification requise"),
            503: ("SERVICE_UNAVAILABLE", "Service indisponible"),
            403: ("FORBIDDEN", "Accès refusé"),
            404: ("NOT_FOUND", "Ressource introuvable"),
            405: ("METHOD_NOT_ALLOWED", "Méthode interdite"),
            415: ("UNSUPPORTED_MEDIA_TYPE", "Format de requête non pris en charge"),
            500: ("INTERNAL_ERROR", "Erreur interne du serveur"),
        }
        if response.status_code in labels and not response.get(
            "Content-Type", ""
        ).startswith("application/json"):
            code, message = labels[response.status_code]
            response.content = json.dumps({"error": {"code": code, "message": message}})
            response["Content-Type"] = "application/json; charset=utf-8"
        return response


class PrivacyHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Referrer-Policy"] = "no-referrer"
        response["Permissions-Policy"] = "microphone=(), geolocation=(), camera=()"
        if request.path.startswith(
            (
                "/api/editor/",
                "/api/docs/",
                "/api/redoc/",
                "/api/swagger",
                "/admin/",
            )
        ):
            response["Cache-Control"] = "no-store, private"
        return response
