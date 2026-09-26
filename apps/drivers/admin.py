
from django.contrib import admin

from apps.drivers.models import DriverLocation, DriverProfile, Vehicle


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "license_number", "is_available", "updated_at")
    list_filter = ("is_available",)
    search_fields = ("user__username", "user__email", "phone", "license_number")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "driver", "vehicle_type", "capacity", "is_active")
    list_filter = ("vehicle_type", "is_active")
    search_fields = ("plate_number", "driver__user__username", "driver__user__email")
    raw_id_fields = ("driver",)
    ordering = ("plate_number",)


@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = ("driver", "latitude", "longitude", "recorded_at")
    list_filter = ("recorded_at",)
    search_fields = ("driver__user__username", "driver__user__email")
    raw_id_fields = ("driver",)
    ordering = ("-recorded_at",)