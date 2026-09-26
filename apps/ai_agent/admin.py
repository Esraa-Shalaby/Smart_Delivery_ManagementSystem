

from django.contrib import admin

from apps.ai_agent.models import AIAction


@admin.register(AIAction)
class AIActionAdmin(admin.ModelAdmin):
    
    list_display = ("action", "user", "success", "created_at")
    list_filter = ("success", "action", "created_at")
    search_fields = ("action", "user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("user", "action", "input", "result", "success", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False