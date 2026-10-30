"""Accès Swagger indépendant des comptes admin : cookie signé court, secret .env.

Jamais de cookie de session Django pour visiter la documentation.
La protection des endpoints JSON et HTML est identique.
"""
import functools
import hmac
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache

COOKIE_NAME = "safidiko_swagger_access"
SIGNER_SALT = "safidiko.swagger.access.v1"
ALLOWED_NEXT = frozenset({"/api/docs/", "/api/redoc/", "/api/swagger.json", "/api/swagger.yaml"})


def valid_next(value):
    return value if value in ALLOWED_NEXT else "/api/docs/"


def has_swagger_access(request):
    password = settings.SWAGGER_PASSWORD
    if not password or len(password) < 12:
        return False
    raw = request.COOKIES.get(COOKIE_NAME, "")
    if not raw or len(raw) > 400:
        return False
    try:
        value = signing.TimestampSigner(salt=SIGNER_SALT).unsign(
            raw, max_age=settings.SWAGGER_COOKIE_MAX_AGE
        )
    except (signing.BadSignature, signing.SignatureExpired):
        return False
    return hmac.compare_digest(value, "swagger-granted-v1")


def grant_swagger_access(response):
    signed = signing.TimestampSigner(salt=SIGNER_SALT).sign("swagger-granted-v1")
    response.set_cookie(
        COOKIE_NAME,
        signed,
        max_age=settings.SWAGGER_COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Strict",
        path="/api/",
    )
    response["Cache-Control"] = "no-store, private"
    return response


def swagger_password_protect(view):
    @functools.wraps(view, updated=())
    @never_cache
    def guarded(request, *args, **kwargs):
        if not settings.SWAGGER_PASSWORD or len(settings.SWAGGER_PASSWORD) < 12:
            return JsonResponse(
                {"error": {"code": "SWAGGER_NOT_CONFIGURED", "message": "Protection Swagger non configurée"}},
                status=503,
            )
        if has_swagger_access(request):
            return view(request, *args, **kwargs)
        if request.path in ("/api/docs/", "/api/redoc/"):
            return redirect("/api/swagger/login/?" + urlencode({"next": request.path}))
        return JsonResponse(
            {"error": {"code": "SWAGGER_AUTH_REQUIRED", "message": "Accès Swagger requis"}},
            status=401,
        )
    return guarded
