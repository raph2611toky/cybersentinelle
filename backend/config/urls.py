from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.conf.urls.static import static
from apps.core.views import VisitorSessionView
from django.conf import settings
from django.urls import path, include
from config.swagger import schema_view

admin.site.site_header = "SAFIDIKO — Administration"
admin.site.site_title = "SAFIDIKO"
admin.site.index_title = "Contenus et permissions"
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/editor/", include("config.editor_urls")),
    path("api/session/", VisitorSessionView.as_view(), name="visitor-session"),
    path("api/v1/", include("apps.content_api.urls")),
    path("api/v1/", include("apps.resources.urls")),
    path("api/v1/", include("apps.pedagogie.urls")),
    path("api/v1/", include("apps.publication.urls")),
]
if settings.SWAGGER_ENABLED:
    urlpatterns += [
        path(
            "api/docs/",
            staff_member_required(schema_view.with_ui("swagger", cache_timeout=0)),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            staff_member_required(schema_view.with_ui("redoc", cache_timeout=0)),
            name="redoc",
        ),
        path(
            "api/swagger.json",
            staff_member_required(schema_view.without_ui(cache_timeout=0)),
            kwargs={"format": "json"},
            name="swagger-json",
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
