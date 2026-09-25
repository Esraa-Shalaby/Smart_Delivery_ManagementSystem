"""
Models for the shipments app.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Shipment(models.Model):
    """
    A delivery request created by a customer.

    Driver assignment is intentionally not modeled here; it will be
    handled by a separate DeliveryAssignment model.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        PICKED_UP = "PICKED_UP", "Picked Up"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shipments",
        limit_choices_to={"role": "CUSTOMER"},
    )

    tracking_number = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        default=uuid.uuid4,
    )

    pickup_address = models.TextField()
    delivery_address = models.TextField()
    package_description = models.TextField(blank=True)

    package_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Weight in kilograms.",
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["tracking_number"]),
        ]

    def __str__(self):
        return f"{self.tracking_number} ({self.status})"

    def clean(self):
        if self.customer_id and getattr(self.customer, "role", None) != "CUSTOMER":
            raise ValidationError({"customer": "Only users with the CUSTOMER role can own shipments."})