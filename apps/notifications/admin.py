from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "title",
        "notification_type",
        "related_object_id",
        "is_read",
        "created_at",
        "read_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__email")
    readonly_fields = ("created_at", "read_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("recipient",)
    actions = ["mark_as_read", "mark_as_unread"]

    @admin.action(description="Mark selected notifications as read")
    def mark_as_read(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        self.message_user(request, f"{updated} notification(s) marked as read.")

    @admin.action(description="Mark selected notifications as unread")
    def mark_as_unread(self, request, queryset):
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f"{updated} notification(s) marked as unread.")