 
from django.urls import path

from apps.complaints.views import (
    ComplaintDetailView,
    ComplaintListCreateView,
    ComplaintResolveView,
    ComplaintRespondView,
    ComplaintStatusUpdateView,
)

app_name = "complaints"

urlpatterns = [
    path("", ComplaintListCreateView.as_view(), name="complaint-list-create"),
    path("<int:pk>/", ComplaintDetailView.as_view(), name="complaint-detail"),
    path("<int:pk>/respond/", ComplaintRespondView.as_view(), name="complaint-respond"),
    path("<int:pk>/status/", ComplaintStatusUpdateView.as_view(), name="complaint-status-update"),
    path("<int:pk>/resolve/", ComplaintResolveView.as_view(), name="complaint-resolve"),
]