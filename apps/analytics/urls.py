from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("shipments/", views.ShipmentStatisticsView.as_view(), name="shipments"),
    path("drivers/", views.DriverStatisticsView.as_view(), name="drivers"),
    path("payments/", views.PaymentStatisticsView.as_view(), name="payments"),
    path("complaints/", views.ComplaintStatisticsView.as_view(), name="complaints"),
    path("dashboard/", views.DashboardSummaryView.as_view(), name="dashboard"),
]