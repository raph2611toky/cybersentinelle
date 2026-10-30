from django.contrib import admin
from .models import VersionContenu, FichierContenu


@admin.register(VersionContenu)
class VersionContenuAdmin(admin.ModelAdmin):
    list_display = ("numero", "statut", "updated_at")
    search_fields = ("numero",)
    list_filter = ("statut",)
    readonly_fields = ("id", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FichierContenu)
class FichierContenuAdmin(admin.ModelAdmin):
    list_display = ("type", "updated_at")
    search_fields = ("chemin",)
    list_filter = ("type",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("version",)

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
