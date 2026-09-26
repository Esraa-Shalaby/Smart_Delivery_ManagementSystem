 

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.drivers.models import DriverLocation, DriverProfile
from apps.shipments.models import DeliveryAssignment


@transaction.atomic
def create_or_update_driver_profile(*, user, **data):
    """
    Creates the driver's profile if it doesn't exist yet, or updates it
    in place otherwise.
    """
    if user.role != "DRIVER":
        raise ValidationError("Only users with the DRIVER role can have a driver profile.")

    profile, _created = DriverProfile.objects.get_or_create(user=user)
    for field, value in data.items():
        setattr(profile, field, value)

    profile.full_clean()
    profile.save()
    return profile


@transaction.atomic
def update_driver_availability(*, driver_profile, is_available):
    """
    Flips the driver's availability flag.
    """
    driver_profile.is_available = is_available
    driver_profile.full_clean()
    driver_profile.save(update_fields=["is_available", "updated_at"])
    return driver_profile


@transaction.atomic
def update_driver_location(*, driver_profile, latitude, longitude):
    """
    Updates the driver's current coordinates and appends a
    DriverLocation history record.
    """
    driver_profile.current_latitude = latitude
    driver_profile.current_longitude = longitude
    driver_profile.full_clean()
    driver_profile.save(update_fields=["current_latitude", "current_longitude", "updated_at"])

    return DriverLocation.objects.create(
        driver=driver_profile, latitude=latitude, longitude=longitude
    )


def get_available_drivers():
    
    return DriverProfile.objects.filter(is_available=True).select_related("user")


def get_driver_details(*, driver_profile_id):
   
    return DriverProfile.objects.select_related("user").prefetch_related("vehicles").get(
        pk=driver_profile_id
    )


def get_driver_assigned_deliveries(*, driver_user):
    
    return DeliveryAssignment.objects.filter(
        driver=driver_user, is_active=True
    ).select_related("shipment")


def get_driver_history(*, driver_user):
    
    return (
        DeliveryAssignment.objects.filter(driver=driver_user, is_active=False)
        .select_related("shipment")
        .order_by("-assigned_at")
    )