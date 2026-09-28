 

from django.contrib import admin

from apps.complaints.models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "customer", "status", "priority", "created_at", "resolved_at")
    list_filter = ("status", "priority", "created_at")
    search_fields = ("subject", "description", "customer__username", "customer__email")
    raw_id_fields = ("customer", "shipment", "resolved_by")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)