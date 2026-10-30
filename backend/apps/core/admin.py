from django.contrib import admin
from .models import Langue


@admin.register(Langue)
class LangueAdmin(admin.ModelAdmin):
    list_display = ("code", "nom_fr", "actif", "updated_at")
    search_fields = ("code", "nom_fr")
    list_filter = ("actif",)
    readonly_fields = ("id", "created_at", "updated_at")
