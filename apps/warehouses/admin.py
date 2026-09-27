from django.contrib import admin

from .models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "city",
        "phone",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "city")
    search_fields = ("name", "code", "city", "address", "phone")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)
    date_hierarchy = "created_at"
    list_editable = ("is_active",)
    actions = ["activate_warehouses", "deactivate_warehouses"]

    @admin.action(description="Activate selected warehouses")
    def activate_warehouses(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} warehouse(s) activated.")

    @admin.action(description="Deactivate selected warehouses")
    def deactivate_warehouses(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} warehouse(s) deactivated.")