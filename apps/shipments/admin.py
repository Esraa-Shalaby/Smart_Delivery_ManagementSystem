"""
Django admin configuration for the shipments app.
"""

from django.contrib import admin

from apps.shipments.models import DeliveryAssignment, Shipment, ShipmentStatusHistory


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("tracking_number", "customer", "status", "delivery_fee", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("tracking_number", "customer__username", "customer__email")
    raw_id_fields = ("customer",)
    readonly_fields = ("tracking_number", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ("shipment", "driver", "assigned_by", "is_active", "assigned_at", "completed_at")
    list_filter = ("is_active", "assigned_at")
    search_fields = ("shipment__tracking_number", "driver__username", "driver__email")
    raw_id_fields = ("shipment", "driver", "assigned_by")
    ordering = ("-assigned_at",)


@admin.register(ShipmentStatusHistory)
class ShipmentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("shipment", "old_status", "new_status", "changed_by", "changed_at")
    list_filter = ("new_status", "changed_at")
    search_fields = ("shipment__tracking_number",)
    raw_id_fields = ("shipment", "changed_by")
    ordering = ("-changed_at",)