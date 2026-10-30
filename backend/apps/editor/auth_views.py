"""Connexion au studio : session Django HttpOnly + protection CSRF.

Aucune identité de mineur ni donnée de joueur n'est acceptée par ces routes.
"""
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from helpers.api.responses import error
from .auth_swagger import csrf_doc, login_doc, me_doc, logout_doc


def _staff_data(user):
    return {"id": str(user.pk), "username": user.get_username(),
            "name": user.get_full_name() or user.get_username(),
            "email": user.email, "is_staff": user.is_staff,
            "role": "Administrateur" if user.is_superuser else "Éditeur",
            "permissions": sorted(user.get_all_permissions())}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AdminCSRFAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @csrf_doc
    def get(self, request):
        try:
            # Assure l'émission d'un csrftoken ; ne pas révéler de cookie de session.
            get_token(request)
            return Response({"csrf": "ready"})
        except Exception:
            return error(500, "INTERNAL_ERROR", "Impossible de préparer la protection CSRF")


@method_decorator(csrf_protect, name="dispatch")
class AdminLoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @login_doc
    def post(self, request):
        try:
            identity = str(request.data.get("username") or request.data.get("email") or "").strip()
            password = request.data.get("password")
            if not identity or not isinstance(password, str) or not password:
                return error(400, "BAD_REQUEST", "Identifiant et mot de passe requis")
            username = identity
            if "@" in identity:
                matches = list(get_user_model().objects.filter(email__iexact=identity, is_active=True, is_staff=True).values_list('username', flat=True)[:2])
                if len(matches) == 1:
                    username = matches[0]
            user = authenticate(request, username=username, password=password)
            if user is None or not user.is_active or not user.is_staff:
                return error(401, "INVALID_CREDENTIALS", "Identifiants invalides")
            login(request, user)
            request.session.set_expiry(0)
            return Response({"user": _staff_data(user)})
        except Exception:
            return error(500, "INTERNAL_ERROR", "Connexion indisponible")


class AdminMeAPIView(APIView):
    permission_classes = [IsAdminUser]

    @me_doc
    def get(self, request):
        try:
            return Response({"user": _staff_data(request.user)})
        except Exception:
            return error(500, "INTERNAL_ERROR", "Lecture du profil indisponible")


@method_decorator(csrf_protect, name="dispatch")
class AdminLogoutAPIView(APIView):
    permission_classes = [IsAdminUser]

    @logout_doc
    def post(self, request):
        try:
            logout(request)
            return Response({"logged_out": True})
        except Exception:
            return error(500, "INTERNAL_ERROR", "Déconnexion indisponible")
