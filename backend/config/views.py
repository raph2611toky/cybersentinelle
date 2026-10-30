"""Seulement les vues transversales du projet ; une méthode HTTP par APIView."""
import hmac
import logging

from django.conf import settings
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from helpers.api.swagger_access import (valid_next, grant_swagger_access, COOKIE_NAME)
from helpers.api.responses import error
from helpers.api.swagger_views import health_docs, login_page_docs, unlock_docs, logout_docs

log = logging.getLogger("safidiko")


class HealthCheckAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @health_docs
    def get(self, request):
        try:
            return Response({"status": "ok"}, status=200)
        except Exception:
            log.exception("Erreur healthcheck")
            return error(500, "INTERNAL_ERROR", "Erreur interne du serveur")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SwaggerLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @login_page_docs
    def get(self, request):
        try:
            response = render(request, "swagger_login.html", {
                "next_url": valid_next(request.GET.get("next", "")),
                "configured": bool(settings.SWAGGER_PASSWORD and len(settings.SWAGGER_PASSWORD) >= 12),
            })
            response["Cache-Control"] = "no-store, private"
            return response
        except Exception:
            log.exception("Erreur dans la page de connexion Swagger")
            return error(500, "INTERNAL_ERROR", "Erreur interne du serveur")


@method_decorator(csrf_protect, name="dispatch")
class SwaggerUnlockAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @unlock_docs
    def post(self, request):
        try:
            password = settings.SWAGGER_PASSWORD
            if not password or len(password) < 12:
                return error(503, "SWAGGER_NOT_CONFIGURED", "Protection Swagger non configurée")
            entered = request.data.get("password", "")
            if not isinstance(entered, str) or not entered:
                return error(400, "BAD_REQUEST", "Mot de passe requis")
            if not hmac.compare_digest(entered.encode("utf-8"), password.encode("utf-8")):
                return error(401, "SWAGGER_BAD_PASSWORD", "Mot de passe incorrect")
            response = Response({
                "authenticated": True,
                "redirect": valid_next(request.data.get("next", "")),
            }, status=200)
            return grant_swagger_access(response)
        except Exception:
            log.exception("Erreur interne d'authentification Swagger")
            return error(500, "INTERNAL_ERROR", "Erreur interne du serveur")


@method_decorator(csrf_protect, name="dispatch")
class SwaggerLogoutAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @logout_docs
    def post(self, request):
        try:
            response = Response({"authenticated": False}, status=200)
            response.delete_cookie(COOKIE_NAME, path="/api/", samesite="Strict")
            response["Cache-Control"] = "no-store, private"
            return response
        except Exception:
            log.exception("Erreur de fermeture d'accès Swagger")
            return error(500, "INTERNAL_ERROR", "Erreur interne du serveur")
