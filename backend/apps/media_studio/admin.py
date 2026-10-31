from django.contrib import admin
from .models import MediaAsset, VoiceProfile, SceneMedia, DialogueLine, GenerationJob


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type', 'origine', 'langue', 'taille_octets', 'created_at')
    list_filter = ('type', 'origine', 'langue')
    search_fields = ('titre', 'sha256')
    readonly_fields = ('id', 'sha256', 'taille_octets', 'mime_type', 'created_at', 'updated_at')
    # L'upload validé doit passer par l'API. L'admin ne contourne pas les contrôles MIME/FFprobe.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    list_display = ('nom', 'provider', 'model_id', 'langue', 'actif')
    list_filter = ('provider', 'langue', 'actif')
    search_fields = ('nom', 'voice_id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(SceneMedia)
class SceneMediaAdmin(admin.ModelAdmin):
    list_display = ('noeud', 'langue', 'mode', 'statut')
    list_filter = ('mode', 'statut', 'langue')
    readonly_fields = ('id', 'created_at', 'updated_at', 'statut', 'video_finale', 'audio_finale')


@admin.register(DialogueLine)
class DialogueLineAdmin(admin.ModelAdmin):
    list_display = ('scene', 'ordre', 'personnage')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'statut', 'created_at', 'fin_le')
    list_filter = ('type', 'statut')
    readonly_fields = ('id', 'type', 'scene', 'voix', 'texte', 'statut', 'resultat', 'code_erreur', 'debut_le', 'fin_le', 'created_at', 'updated_at')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
