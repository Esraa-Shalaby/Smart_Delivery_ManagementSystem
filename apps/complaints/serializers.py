 

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.complaints.models import Complaint
from apps.complaints.services import create_complaint


class ComplaintSerializer(serializers.ModelSerializer):
    

    customer = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    shipment_tracking_number = serializers.CharField(
        source="shipment.tracking_number", read_only=True, default=None
    )

    class Meta:
        model = Complaint
        fields = [
            "id",
            "customer",
            "shipment",
            "shipment_tracking_number",
            "subject",
            "description",
            "status",
            "priority",
            "response",
            "resolved_by",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "status",
            "response",
            "resolved_by",
            "created_at",
            "updated_at",
            "resolved_at",
        ]


class ComplaintCreateSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = Complaint
        fields = ["shipment", "subject", "description", "priority"]

    def create(self, validated_data):
        request = self.context["request"]
        return create_complaint(customer=request.user, **validated_data)


class ComplaintRespondSerializer(serializers.Serializer):
    

    response = serializers.CharField()


class ComplaintStatusUpdateSerializer(serializers.Serializer):
    

    status = serializers.ChoiceField(choices=Complaint.Status.choices)


class ComplaintResolveSerializer(serializers.Serializer):
   

    response = serializers.CharField(required=False, allow_blank=True, default="")