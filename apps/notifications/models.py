from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        SHIPMENT_CREATED = "SHIPMENT_CREATED", "Shipment created"
        DRIVER_ASSIGNED = "DRIVER_ASSIGNED", "Driver assigned"
        SHIPMENT_STATUS_CHANGED = "SHIPMENT_STATUS_CHANGED", "Shipment status changed"
        DELIVERY_DELAYED = "DELIVERY_DELAYED", "Delivery delayed"
        PAYMENT_UPDATED = "PAYMENT_UPDATED", "Payment updated"
        COMPLAINT_UPDATED = "COMPLAINT_UPDATED", "Complaint updated"
        SYSTEM = "SYSTEM", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        help_text=(
            "The user this notification is for. Left null for system-wide "
            "broadcast notifications (notification_type=SYSTEM) that aren't "
            "targeted at one specific user."
        ),
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Id of the related object (shipment, payment, complaint, ...).",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        target = self.recipient_id or "broadcast"
        return f"[{self.notification_type}] {self.title} -> {target}"

    def clean(self):
        errors = {}
        if not self.title or not self.title.strip():
            errors["title"] = "Title cannot be blank."
        if not self.message or not self.message.strip():
            errors["message"] = "Message cannot be blank."
        if self.recipient_id is None and self.notification_type != self.NotificationType.SYSTEM:
            errors["recipient"] = (
                "Only SYSTEM notifications may be created without a recipient."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)