 
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DriverProfile(models.Model):
   

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
        limit_choices_to={"role": "DRIVER"},
    )

    phone = models.CharField(max_length=20)
    license_number = models.CharField(max_length=50, unique=True)
    vehicle = models.CharField(
        max_length=100, blank=True, help_text="Short vehicle description."
    )
    is_available = models.BooleanField(default=False)

    current_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    current_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["is_available"])]

    def __str__(self):
        return f"Driver profile: {self.user}"

    def clean(self):
        if self.user_id and getattr(self.user, "role", None) != "DRIVER":
            raise ValidationError(
                {"user": "Only users with the DRIVER role can have a driver profile."}
            )


class Vehicle(models.Model):
    """
    A vehicle registered to a driver. A driver may have more than one
    over time; `is_active` marks the one currently in use.
    """

    driver = models.ForeignKey(
        DriverProfile, on_delete=models.CASCADE, related_name="vehicles"
    )
    vehicle_type = models.CharField(max_length=50)
    plate_number = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=100, blank=True)
    capacity = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Maximum load in kilograms."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["driver", "is_active"])]

    def __str__(self):
        return f"{self.plate_number} ({self.driver})"


class DriverLocation(models.Model):
    """
    Historical trail of a driver's reported locations.
    """

    driver = models.ForeignKey(
        DriverProfile, on_delete=models.CASCADE, related_name="location_history"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["driver", "recorded_at"])]

    def __str__(self):
        return f"{self.driver} @ ({self.latitude}, {self.longitude})"