from .forms import VisuelAdminForm
from django.contrib import admin
from .models import Sujet, Visuel, Tantara, Noeud, OptionDecision


@admin.register(Sujet)
class SujetAdmin(admin.ModelAdmin):
    list_display = ("code", "actif", "updated_at")
    search_fields = ("code",)
    list_filter = ("actif",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Visuel)
class VisuelAdmin(admin.ModelAdmin):
    form = VisuelAdminForm
    list_display = ("code", "type", "actif", "updated_at")
    search_fields = ("code",)
    list_filter = ("actif", "type")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Tantara)
class TantaraAdmin(admin.ModelAdmin):
    list_display = ("slug", "numero", "titre_fr", "statut_editorial", "updated_at")
    search_fields = ("slug", "numero", "titre_fr")
    list_filter = ("statut_editorial",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("visuel_heros",)
    filter_horizontal = ("sujets",)


@admin.register(Noeud)
class NoeudAdmin(admin.ModelAdmin):
    list_display = ("cle", "titre_fr", "type", "updated_at")
    search_fields = ("cle", "titre_fr")
    list_filter = ("type",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("tantara", "visuel", "noeud_suivant")


@admin.register(OptionDecision)
class OptionDecisionAdmin(admin.ModelAdmin):
    list_display = ("cle", "updated_at")
    search_fields = ("cle",)
    list_filter = ()
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("noeud", "noeud_cible")
