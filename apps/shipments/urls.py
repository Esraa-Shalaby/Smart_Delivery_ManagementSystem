"""
URL routing for the shipments app.
"""

from django.urls import path

from apps.shipments.views import (
    AssignDriverView,
    ReassignDriverView,
    ShipmentDetailView,
    ShipmentListCreateView,
    ShipmentStatusHistoryView,
    ShipmentTrackingView,
    UpdateShipmentStatusView,
)

app_name = "shipments"

urlpatterns = [
    path("", ShipmentListCreateView.as_view(), name="shipment-list-create"),
    path("<int:pk>/", ShipmentDetailView.as_view(), name="shipment-detail"),
    path("<int:pk>/tracking/", ShipmentTrackingView.as_view(), name="shipment-tracking"),
    path("<int:pk>/history/", ShipmentStatusHistoryView.as_view(), name="shipment-history"),
    path("<int:pk>/assign/", AssignDriverView.as_view(), name="shipment-assign"),
    path("<int:pk>/reassign/", ReassignDriverView.as_view(), name="shipment-reassign"),
    path("<int:pk>/status/", UpdateShipmentStatusView.as_view(), name="shipment-status-update"),
]