from django.contrib import admin
from .models import Source, RessourceAide


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("code", "nom_fr", "type", "actif", "updated_at")
    search_fields = ("code", "nom_fr")
    list_filter = ("actif", "type")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RessourceAide)
class RessourceAideAdmin(admin.ModelAdmin):
    list_display = ("cle", "titre_fr", "statut_editorial", "updated_at")
    search_fields = ("cle", "titre_fr")
    list_filter = ("statut_editorial",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("source", "ressource_repli")
