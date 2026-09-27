from rest_framework import serializers

from . import services
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = [
            "id",
            "shipment",
            "customer",
            "amount",
            "payment_method",
            "status",
            "transaction_reference",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "paid_at",
            "created_at",
            "updated_at",
        ]


class PaymentCreateSerializer(PaymentSerializer):


    class Meta(PaymentSerializer.Meta):
        read_only_fields = PaymentSerializer.Meta.read_only_fields + ["customer"]

    def validate_amount(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value

    def validate_transaction_reference(self, value):
        if value:
            if Payment.objects.filter(transaction_reference=value).exists():
                raise serializers.ValidationError(
                    "This transaction reference is already in use."
                )
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return services.create_payment(
                shipment=validated_data["shipment"],
                customer=request.user,
                amount=validated_data["amount"],
                payment_method=validated_data["payment_method"],
                transaction_reference=validated_data.get("transaction_reference"),
            )
        except services.PaymentError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class PaymentStatusUpdateSerializer(serializers.Serializer):

    status = serializers.ChoiceField(choices=Payment.PaymentStatus.choices)


class PaymentMarkPaidSerializer(serializers.Serializer):

    transaction_reference = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )