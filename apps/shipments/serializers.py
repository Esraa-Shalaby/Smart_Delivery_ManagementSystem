"""
Serializers for the shipments app.

Validation lives here; all persistence and business rules are
delegated to shipments/services.py.
"""

from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.shipments.models import DeliveryAssignment, Shipment, ShipmentStatusHistory
from apps.shipments.services import create_shipment


class ShipmentSerializer(serializers.ModelSerializer):
    """
    Full read representation of a shipment.
    """

    customer = UserSerializer(read_only=True)

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


class ShipmentCreateSerializer(serializers.ModelSerializer):
    """
    Used only for creating a shipment. `customer` is taken from the
    authenticated request user and is never accepted from the client.
    """

    class Meta:
        model = Shipment
        fields = [
            "pickup_address",
            "delivery_address",
            "package_description",
            "package_weight",
            "delivery_fee",
        ]

    def validate_package_weight(self, value):
        if value <= 0:
            raise serializers.ValidationError("Package weight must be greater than zero.")
        return value

    def validate_delivery_fee(self, value):
        if value < 0:
            raise serializers.ValidationError("Delivery fee cannot be negative.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return create_shipment(customer=request.user, **validated_data)


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    """
    Read representation of a driver assignment.
    """

    driver = UserSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)

    class Meta:
        model = DeliveryAssignment
        fields = [
            "id",
            "shipment",
            "driver",
            "assigned_by",
            "assigned_at",
            "accepted_at",
            "completed_at",
            "is_active",
        ]
        read_only_fields = fields


class AssignDriverSerializer(serializers.Serializer):
    """
    Input serializer for assigning/reassigning a driver to a shipment.
    """

    driver = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.DRIVER)
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateShipmentStatusSerializer(serializers.Serializer):
    """
    Input serializer for shipment status transitions.
    """

    status = serializers.ChoiceField(choices=Shipment.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ShipmentStatusHistorySerializer(serializers.ModelSerializer):
    """
    Read representation of a single status-change record.
    """

    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = ShipmentStatusHistory
        fields = ["id", "shipment", "old_status", "new_status", "changed_by", "changed_at", "note"]
        read_only_fields = fields


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    """
    Combines shipment details with its full status history for tracking.
    """

    status_history = ShipmentStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "tracking_number",
            "status",
            "pickup_address",
            "delivery_address",
            "created_at",
            "updated_at",
            "status_history",
        ]
        read_only_fields = fields
