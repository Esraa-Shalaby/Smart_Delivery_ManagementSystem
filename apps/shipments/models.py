"""
Models for the shipments app.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def generate_tracking_number():
    return f"SD{uuid.uuid4().hex[:10].upper()}"


class Shipment(models.Model):
    """
    A delivery request created by a customer. Driver assignment is
    intentionally not modeled here -- see DeliveryAssignment.
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
        default=generate_tracking_number,
    )

    pickup_address = models.TextField()
    delivery_address = models.TextField()
    package_description = models.TextField(blank=True)

    package_weight = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Weight in kilograms."
    )
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)

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
        ]

    def __str__(self):
        return f"{self.tracking_number} ({self.status})"

    def clean(self):
        if self.customer_id and getattr(self.customer, "role", None) != "CUSTOMER":
            raise ValidationError(
                {"customer": "Only users with the CUSTOMER role can own shipments."}
            )


class DeliveryAssignment(models.Model):
    """
    Assigns a driver to a shipment. Reassigning deactivates the previous
    assignment instead of deleting it, so assignment history is preserved.
    """

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="assignments"
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_assignments",
        limit_choices_to={"role": "DRIVER"},
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_made",
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["shipment", "is_active"]),
            models.Index(fields=["driver", "is_active"]),
        ]

    def __str__(self):
        return f"{self.shipment.tracking_number} -> {self.driver} (active={self.is_active})"

    def clean(self):
        if self.driver_id and getattr(self.driver, "role", None) != "DRIVER":
            raise ValidationError(
                {"driver": "Only users with the DRIVER role can be assigned to shipments."}
            )


class ShipmentStatusHistory(models.Model):
    """
    Immutable audit trail of every shipment status change.
    """

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="status_history"
    )
    old_status = models.CharField(max_length=20, choices=Shipment.Status.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=Shipment.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="shipment_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "Shipment status histories"

    def __str__(self):
        return f"{self.shipment.tracking_number}: {self.old_status or ''} -> {self.new_status}"
