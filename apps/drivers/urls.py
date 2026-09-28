"""
URL routing for the drivers app.
"""

from django.urls import path

from apps.drivers.views import (
    AssignedDeliveriesView,
    AvailabilityUpdateView,
    AvailableDriversListView,
    DeliveryHistoryView,
    DriverDetailView,
    DriverProfileView,
    LocationUpdateView,
)

app_name = "drivers"

urlpatterns = [
    path("profile/", DriverProfileView.as_view(), name="driver-profile"),
    path("availability/", AvailabilityUpdateView.as_view(), name="driver-availability"),
    path("location/", LocationUpdateView.as_view(), name="driver-location"),
    path("deliveries/", AssignedDeliveriesView.as_view(), name="driver-deliveries"),
    path("deliveries/history/", DeliveryHistoryView.as_view(), name="driver-delivery-history"),
    path("available/", AvailableDriversListView.as_view(), name="available-drivers"),
    path("<int:pk>/", DriverDetailView.as_view(), name="driver-detail"),
]
