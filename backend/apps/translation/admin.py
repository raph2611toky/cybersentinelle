from django.contrib import admin
from .models import TranslationJob

@admin.register(TranslationJob)
class TranslationJobAdmin(admin.ModelAdmin):
    list_display=('target_type','target_id','state','attempts','created_at')
    list_filter=('state','target_type')
    readonly_fields=('target_type','target_id','path','source_sha256','state','attempts','last_error','created_at','updated_at')
    exclude=('source_text',)
    def has_add_permission(self, request):return False
    def has_change_permission(self, request, obj=None):return False
    def has_delete_permission(self, request, obj=None):return False
