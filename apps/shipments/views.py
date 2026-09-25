"""
API views for the shipments app.

Views stay thin: input validation happens in serializers, business
logic happens in shipments/services.py.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.shipments.models import Shipment
from apps.shipments.permissions import (
    CanUpdateShipmentStatus,
    IsManagerRole,
    IsShipmentParticipant,
)
from apps.shipments.serializers import (
    AssignDriverSerializer,
    DeliveryAssignmentSerializer,
    ShipmentCreateSerializer,
    ShipmentSerializer,
    ShipmentStatusHistorySerializer,
    ShipmentTrackingSerializer,
    UpdateShipmentStatusSerializer,
)
from apps.shipments.services import assign_driver, reassign_driver, update_shipment_status


def _raise_drf_validation(exc):
    """Re-raises a Django ValidationError (from services) as a DRF one."""
    if hasattr(exc, "message_dict"):
        raise DRFValidationError(exc.message_dict)
    raise DRFValidationError(exc.messages)


class ShipmentListCreateView(APIView):
    """
    GET: list shipments visible to the authenticated user's role.
    POST: create a shipment (CUSTOMER only).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.Role.MANAGER:
            queryset = Shipment.objects.all()
        elif user.role == User.Role.CUSTOMER:
            queryset = Shipment.objects.filter(customer=user)
        elif user.role == User.Role.DRIVER:
            queryset = Shipment.objects.filter(
                assignments__driver=user, assignments__is_active=True
            ).distinct()
        else:
            queryset = Shipment.objects.none()

        serializer = ShipmentSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != User.Role.CUSTOMER:
            return Response(
                {"detail": "Only customers can create shipments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ShipmentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            shipment = serializer.save()
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(ShipmentSerializer(shipment).data, status=status.HTTP_201_CREATED)


class ShipmentDetailView(APIView):
    """
    Retrieves a single shipment, restricted to its participants.
    """

    permission_classes = [IsAuthenticated, IsShipmentParticipant]

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        self.check_object_permissions(request, shipment)
        return Response(ShipmentSerializer(shipment).data, status=status.HTTP_200_OK)


class ShipmentTrackingView(APIView):
    """
    Returns shipment details together with its full status history.
    """

    permission_classes = [IsAuthenticated, IsShipmentParticipant]

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        self.check_object_permissions(request, shipment)
        return Response(ShipmentTrackingSerializer(shipment).data, status=status.HTTP_200_OK)


class ShipmentStatusHistoryView(APIView):
    """
    Lists the raw status-change history for a shipment.
    """

    permission_classes = [IsAuthenticated, IsShipmentParticipant]

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        self.check_object_permissions(request, shipment)
        history = shipment.status_history.all()
        return Response(
            ShipmentStatusHistorySerializer(history, many=True).data, status=status.HTTP_200_OK
        )


class AssignDriverView(APIView):
    """
    Assigns a driver to a shipment with no active assignment. MANAGER only.
    """

    permission_classes = [IsAuthenticated, IsManagerRole]

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        serializer = AssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = assign_driver(
                shipment=shipment,
                driver=serializer.validated_data["driver"],
                assigned_by=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(DeliveryAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class ReassignDriverView(APIView):
    """
    Reassigns a shipment to a new driver, preserving prior assignment
    history. MANAGER only.
    """

    permission_classes = [IsAuthenticated, IsManagerRole]

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        serializer = AssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = reassign_driver(
                shipment=shipment,
                new_driver=serializer.validated_data["driver"],
                assigned_by=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(DeliveryAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class UpdateShipmentStatusView(APIView):
    """
    Updates a shipment's status. MANAGER may update any shipment;
    DRIVER may update only shipments currently assigned to them.
    """

    permission_classes = [IsAuthenticated, CanUpdateShipmentStatus]

    def patch(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        self.check_object_permissions(request, shipment)

        serializer = UpdateShipmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            shipment = update_shipment_status(
                shipment=shipment,
                new_status=serializer.validated_data["status"],
                changed_by=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(ShipmentSerializer(shipment).data, status=status.HTTP_200_OK)