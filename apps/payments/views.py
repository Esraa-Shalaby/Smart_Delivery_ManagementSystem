from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Payment
from .permissions import PaymentAccessPermission, _is_manager
from .serializers import (
    PaymentCreateSerializer,
    PaymentMarkPaidSerializer,
    PaymentSerializer,
    PaymentStatusUpdateSerializer,
)


class PaymentViewSet(viewsets.ModelViewSet):
    

    permission_classes = [PaymentAccessPermission]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("shipment", "customer")
        if _is_manager(user):
            return qs
        return qs.filter(customer=user)

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentSerializer

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """Return the authenticated customer's own payment history."""
        payments = services.get_customer_payment_history(request.user)
        page = self.paginate_queryset(payments)
        serializer = PaymentSerializer(page if page is not None else payments, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request, pk=None):
        """Generic status transition. Managers only."""
        if not _is_manager(request.user):
            return Response(
                {"detail": "Only managers can change payment status."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        payment = self.get_object()
        serializer = PaymentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = services.process_payment_status(
                payment, serializer.validated_data["status"]
            )
        except services.PaymentError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """Mark a payment as PAID. Managers only."""
        if not _is_manager(request.user):
            return Response(
                {"detail": "Only managers can mark payments as paid."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        payment = self.get_object()
        serializer = PaymentMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = services.mark_payment_as_paid(
                payment,
                transaction_reference=serializer.validated_data.get("transaction_reference")
                or None,
            )
        except services.PaymentError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"], url_path="refund")
    def refund(self, request, pk=None):
        if not _is_manager(request.user):
            return Response(
                {"detail": "Only managers can refund payments."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        payment = self.get_object()
        try:
            payment = services.refund_payment(payment)
        except services.PaymentError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)