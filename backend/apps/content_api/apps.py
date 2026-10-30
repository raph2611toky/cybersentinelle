from django.apps import AppConfig


class ContentApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content_api"

    def ready(self):
        from . import signals  # noqa: F401
