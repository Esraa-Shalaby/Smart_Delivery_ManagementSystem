from rest_framework import serializers

from . import services
from .models import Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    """Full serializer used for retrieve/list responses and manager writes."""

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "code",
            "address",
            "city",
            "phone",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def validate_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("code is required.")
        qs = Warehouse.objects.filter(code__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This code is already in use.")
        return value.strip().upper()

    def create(self, validated_data):
        try:
            return services.create_warehouse(**validated_data)
        except services.WarehouseError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def update(self, instance, validated_data):
        try:
            return services.update_warehouse(instance, **validated_data)
        except services.WarehouseError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class WarehousePublicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "code",
            "address",
            "city",
            "phone",
            "latitude",
            "longitude",
            "is_active",
        ]
        read_only_fields = fields


class WarehouseStatusActionSerializer(serializers.Serializer):
    pass