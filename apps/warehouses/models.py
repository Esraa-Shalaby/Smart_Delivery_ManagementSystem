from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Warehouse(models.Model):

    name = models.CharField(max_length=150)
    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Short unique code identifying this warehouse (e.g. WH-CAI-01).",
    )
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["city"]),
        ]
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        errors = {}
        if self.code:
            self.code = self.code.strip().upper()
            if not self.code:
                errors["code"] = "Code cannot be blank."
        if not self.name or not self.name.strip():
            errors["name"] = "Name cannot be blank."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)