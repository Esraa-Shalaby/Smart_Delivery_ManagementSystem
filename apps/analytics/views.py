from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class IsManager(BasePermission):
    """Allow only authenticated users whose role is MANAGER."""

    message = "Only managers can access analytics."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        config = services.get_config()
        return getattr(user, config["USER_ROLE_ATTR"], None) == config["MANAGER_ROLE"]


class ManagerAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsManager]


class ShipmentStatisticsView(ManagerAnalyticsView):
    def get(self, request):
        return Response(services.get_shipment_statistics())


class DriverStatisticsView(ManagerAnalyticsView):
    def get(self, request):
        return Response(services.get_driver_statistics())


class PaymentStatisticsView(ManagerAnalyticsView):
    def get(self, request):
        return Response(services.get_payment_statistics())


class ComplaintStatisticsView(ManagerAnalyticsView):
    def get(self, request):
        return Response(services.get_complaint_statistics())


class DashboardSummaryView(ManagerAnalyticsView):
    def get(self, request):
        return Response(services.get_dashboard_summary())