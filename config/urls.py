"""
Main URL configuration for Smart Delivery & Logistics Management System.

Each app owns its own urls.py; this file only wires them together
under their API prefixes. No business logic lives here.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/accounts/", include("apps.accounts.urls")),
    path("api/shipments/", include("apps.shipments.urls")),
    path("api/drivers/", include("apps.drivers.urls")),
    path("api/warehouses/", include("apps.warehouses.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/complaints/", include("apps.complaints.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/ai-agent/", include("apps.ai_agent.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)