"""
Serializers for the shipments app.

Validation lives here; actual creation/update logic is delegated to
shipments/services.py.
"""

from rest_framework import serializers

from apps.shipments.models import Shipment
from apps.shipments.services import create_shipment


class ShipmentSerializer(serializers.ModelSerializer):
    """
    Serializes Shipment instances. `customer` is never accepted from
    the client — it is always taken from the authenticated request user.
    """

    class Meta:
        model = Shipment
        fields = [
            "id",
            "customer",
            "tracking_number",
            "pickup_address",
            "delivery_address",
            "package_description",
            "package_weight",
            "delivery_fee",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "tracking_number",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_package_weight(self, value):
        if value <= 0:
            raise serializers.ValidationError("Package weight must be greater than zero.")
        return value

    def validate_delivery_fee(self, value):
        if value < 0:
            raise serializers.ValidationError("Delivery fee cannot be negative.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")

        if self.instance is None and request.user.role != "CUSTOMER":
            raise serializers.ValidationError(
                "Only users with the CUSTOMER role can create shipments."
            )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return create_shipment(customer=request.user, **validated_data)