from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        ONLINE = "ONLINE", "Online"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"
        CANCELLED = "CANCELLED", "Cancelled"

    shipment = models.ForeignKey(
        "shipments.Shipment",
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="The shipment this payment is for.",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="The customer who owns this payment.",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    transaction_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="External/gateway transaction reference. Must be unique when set.",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["shipment"]),
        ]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment #{self.pk} - shipment {self.shipment_id} - {self.status}"

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount < 0:
            errors["amount"] = "Amount cannot be negative."
        if self.shipment_id is None:
            errors["shipment"] = "Payment must belong to a shipment."
        if self.customer_id is None:
            errors["customer"] = "Payment must belong to a customer."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)