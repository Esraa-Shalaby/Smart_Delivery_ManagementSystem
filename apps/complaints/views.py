 

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.complaints.models import Complaint
from apps.complaints.permissions import IsComplaintParticipant, IsManagerRole
from apps.complaints.serializers import (
    ComplaintCreateSerializer,
    ComplaintResolveSerializer,
    ComplaintRespondSerializer,
    ComplaintSerializer,
    ComplaintStatusUpdateSerializer,
)
from apps.complaints.services import (
    list_all_complaints,
    list_customer_complaints,
    resolve_complaint,
    respond_to_complaint,
    update_complaint_status,
)


def _raise_drf_validation(exc):
    
    if hasattr(exc, "message_dict"):
        raise DRFValidationError(exc.message_dict)
    raise DRFValidationError(exc.messages)


class ComplaintListCreateView(APIView):
     

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.Role.MANAGER:
            queryset = list_all_complaints()
        elif user.role == User.Role.CUSTOMER:
            queryset = list_customer_complaints(customer=user)
        else:
            return Response(
                {"detail": "Drivers cannot access complaint data."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(ComplaintSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != User.Role.CUSTOMER:
            return Response(
                {"detail": "Only customers can file complaints."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ComplaintCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            complaint = serializer.save()
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)


class ComplaintDetailView(APIView):
     
    permission_classes = [IsAuthenticated, IsComplaintParticipant]

    def get(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        self.check_object_permissions(request, complaint)
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)


class ComplaintRespondView(APIView):
    

    permission_classes = [IsAuthenticated, IsManagerRole]

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            complaint = respond_to_complaint(
                complaint=complaint,
                response=serializer.validated_data["response"],
                responded_by=request.user,
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)


class ComplaintStatusUpdateView(APIView):
     

    permission_classes = [IsAuthenticated, IsManagerRole]

    def patch(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            complaint = update_complaint_status(
                complaint=complaint,
                new_status=serializer.validated_data["status"],
                changed_by=request.user,
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)


class ComplaintResolveView(APIView):
     

    permission_classes = [IsAuthenticated, IsManagerRole]

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            complaint = resolve_complaint(
                complaint=complaint,
                resolved_by=request.user,
                response=serializer.validated_data.get("response", ""),
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)