"""
Django admin configuration for the accounts app.
"""

from django.contrib import admin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Admin configuration for the custom User model.
    Password is never exposed through this interface.
    """

    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email", "role")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("username", "email", "role")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )