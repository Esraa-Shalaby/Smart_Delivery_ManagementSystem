from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shipment",
        "customer",
        "amount",
        "payment_method",
        "status",
        "transaction_reference",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = (
        "id",
        "transaction_reference",
        "customer__email",
        "shipment__id",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("shipment", "customer")