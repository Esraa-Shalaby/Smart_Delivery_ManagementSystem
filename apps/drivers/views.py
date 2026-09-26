 

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import DriverProfile
from apps.drivers.permissions import IsDriverOwnerOrManager, IsDriverRole, IsManagerRole
from apps.drivers.serializers import (
    AvailabilityUpdateSerializer,
    DriverProfileSerializer,
    DriverProfileWriteSerializer,
    LocationUpdateSerializer,
)
from apps.drivers.services import (
    create_or_update_driver_profile,
    get_available_drivers,
    get_driver_assigned_deliveries,
    get_driver_history,
    update_driver_availability,
    update_driver_location,
)
from apps.shipments.serializers import DeliveryAssignmentSerializer


def _raise_drf_validation(exc):
    """Re-raises a Django ValidationError (from services) as a DRF one."""
    if hasattr(exc, "message_dict"):
        raise DRFValidationError(exc.message_dict)
    raise DRFValidationError(exc.messages)


class DriverProfileView(APIView):
     

    permission_classes = [IsAuthenticated, IsDriverRole]

    def get(self, request):
        profile = get_object_or_404(DriverProfile, user=request.user)
        return Response(DriverProfileSerializer(profile).data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = DriverProfileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = create_or_update_driver_profile(user=request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(DriverProfileSerializer(profile).data, status=status.HTTP_200_OK)


class AvailabilityUpdateView(APIView):
    

    permission_classes = [IsAuthenticated, IsDriverRole]

    def patch(self, request):
        profile = get_object_or_404(DriverProfile, user=request.user)
        serializer = AvailabilityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = update_driver_availability(
                driver_profile=profile, is_available=serializer.validated_data["is_available"]
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(DriverProfileSerializer(profile).data, status=status.HTTP_200_OK)


class LocationUpdateView(APIView):
     

    permission_classes = [IsAuthenticated, IsDriverRole]

    def post(self, request):
        profile = get_object_or_404(DriverProfile, user=request.user)
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            update_driver_location(
                driver_profile=profile,
                latitude=serializer.validated_data["latitude"],
                longitude=serializer.validated_data["longitude"],
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        profile.refresh_from_db()
        return Response(DriverProfileSerializer(profile).data, status=status.HTTP_200_OK)


class AssignedDeliveriesView(APIView):
    
    permission_classes = [IsAuthenticated, IsDriverRole]

    def get(self, request):
        assignments = get_driver_assigned_deliveries(driver_user=request.user)
        return Response(
            DeliveryAssignmentSerializer(assignments, many=True).data, status=status.HTTP_200_OK
        )


class DeliveryHistoryView(APIView):
     

    permission_classes = [IsAuthenticated, IsDriverRole]

    def get(self, request):
        assignments = get_driver_history(driver_user=request.user)
        return Response(
            DeliveryAssignmentSerializer(assignments, many=True).data, status=status.HTTP_200_OK
        )


class AvailableDriversListView(APIView):
     
    permission_classes = [IsAuthenticated, IsManagerRole]

    def get(self, request):
        drivers = get_available_drivers()
        return Response(DriverProfileSerializer(drivers, many=True).data, status=status.HTTP_200_OK)


class DriverDetailView(APIView):
    

    permission_classes = [IsAuthenticated, IsDriverOwnerOrManager]

    def get(self, request, pk):
        profile = get_object_or_404(DriverProfile, pk=pk)
        self.check_object_permissions(request, profile)
        return Response(DriverProfileSerializer(profile).data, status=status.HTTP_200_OK)