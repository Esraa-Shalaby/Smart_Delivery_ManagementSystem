

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.drivers.models import DriverLocation, DriverProfile, Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ["id", "driver", "vehicle_type", "plate_number", "model", "capacity", "is_active"]
        read_only_fields = ["id", "driver"]


class DriverLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverLocation
        fields = ["id", "driver", "latitude", "longitude", "recorded_at"]
        read_only_fields = fields


class DriverProfileSerializer(serializers.ModelSerializer):
   

    user = UserSerializer(read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True)

    class Meta:
        model = DriverProfile
        fields = [
            "id",
            "user",
            "phone",
            "license_number",
            "vehicle",
            "is_available",
            "current_latitude",
            "current_longitude",
            "vehicles",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "is_available",
            "current_latitude",
            "current_longitude",
            "vehicles",
            "created_at",
            "updated_at",
        ]


class DriverProfileWriteSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = DriverProfile
        fields = ["phone", "license_number", "vehicle"]


class AvailabilityUpdateSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)