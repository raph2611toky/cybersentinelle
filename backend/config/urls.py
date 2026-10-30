"""Point d'entrée unique : routes publiques, édition, Django Admin, Swagger et médias dev."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from config.views import (
    HealthCheckAPIView, SwaggerLoginAPIView, SwaggerUnlockAPIView, SwaggerLogoutAPIView,
)
from helpers.api.swagger import schema_view
from helpers.api.swagger_access import swagger_password_protect

admin.site.site_header = "SAFIDIKO — Administration"
admin.site.site_title = "SAFIDIKO"
admin.site.index_title = "Contenus et permissions"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckAPIView.as_view(), name="healthcheck"),
    path("api/editor/", include("apps.editor.urls")),
    path("api/v1/", include("apps.content_api.urls")),
    path("api/v1/", include("apps.resources.urls")),
    path("api/v1/", include("apps.pedagogie.urls")),
    path("api/v1/", include("apps.publication.urls")),
]

if settings.SWAGGER_ENABLED:
    urlpatterns += [
        path("api/swagger/login/", SwaggerLoginAPIView.as_view(), name="swagger-login"),
        path("api/swagger/unlock/", SwaggerUnlockAPIView.as_view(), name="swagger-unlock"),
        path("api/swagger/logout/", SwaggerLogoutAPIView.as_view(), name="swagger-logout"),
        path("api/docs/", swagger_password_protect(schema_view.with_ui("swagger", cache_timeout=0)), name="swagger-ui"),
        path("api/redoc/", swagger_password_protect(schema_view.with_ui("redoc", cache_timeout=0)), name="redoc"),
        re_path(r"^api/swagger(?P<format>\.json|\.yaml)$", swagger_password_protect(schema_view.without_ui(cache_timeout=0)), name="swagger-schema"),
    ]

# django.views.static.serve ne convient qu'au développement.
if settings.DEBUG and settings.MEDIA_URL.startswith("/"):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
