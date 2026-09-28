
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.shipments.models import Shipment


class Complaint(models.Model):
    

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="complaints",
        limit_choices_to={"role": "CUSTOMER"},
    )
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        help_text="Optional — leave blank for a complaint not tied to a specific shipment.",
    )

    subject = models.CharField(max_length=150)
    description = models.TextField()

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True
    )

    response = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_complaints",
        limit_choices_to={"role": "MANAGER"},
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"Complaint #{self.pk} ({self.status}): {self.subject}"

    def clean(self):
        if self.customer_id and getattr(self.customer, "role", None) != "CUSTOMER":
            raise ValidationError(
                {"customer": "Only users with the CUSTOMER role can file complaints."}
            )
        if self.shipment_id and self.customer_id and self.shipment.customer_id != self.customer_id:
            raise ValidationError(
                {"shipment": "You can only file a complaint about your own shipment."}
            )