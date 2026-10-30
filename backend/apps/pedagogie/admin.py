from django.contrib import admin
from .models import QuestionPedagogique


@admin.register(QuestionPedagogique)
class QuestionPedagogiqueAdmin(admin.ModelAdmin):
    list_display = ("cle", "statut_editorial", "updated_at")
    search_fields = ("cle",)
    list_filter = ("statut_editorial",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("sujet",)
    filter_horizontal = ("ressources_liees",)
