from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from . import driver_views as dv
from . import manager_views as mv
from . import views as v
from .views import ByRolePage, action_stub, page

C, D, M = "CUSTOMER", "DRIVER", "MANAGER"


def build(role, rows):
    return [
        path(route, page(tpl, role) if tpl else action_stub, name=name)
        for route, name, tpl in rows
    ]


def crud(plural, one, list_t, detail_t=None, create=True):
    detail_t = detail_t or list_t
    return [
        (f"{plural}/", plural, list_t),
        *([(f"{plural}/new/", f"{one}_create", list_t)] if create else []),
        (f"{plural}/<int:pk>/", f"{one}_detail", detail_t),
        (f"{plural}/<int:pk>/edit/", f"{one}_edit", list_t),
        (f"{plural}/<int:pk>/activate/", f"{one}_activate", None),
        (f"{plural}/<int:pk>/deactivate/", f"{one}_deactivate", None),
    ]


profile_view = ByRolePage.as_view(templates={
    C: "customer/profile.html",
    D: "driver/profile.html",
    M: "manager/profile.html",
})
notif_view = ByRolePage.as_view(templates={
    C: "customer/notification.html",
    D: "driver/notifications.html",
    M: "manager/notifications.html",
})

# ---------------- accounts ----------------
accounts_urls = ([
    path("login/", v.LoginView.as_view(), name="login"),
    path("logout/", v.logout_view, name="logout"),
    path("register/", v.RegisterView.as_view(), name="register"),
    path("password-reset/", v.PasswordResetPage.as_view(), name="password_reset"),
    path("password-change/", v.PasswordChangePage.as_view(), name="password_change"),
    path("profile/", v.ProfileView.as_view(), name="profile"),
], "accounts")

# ---------------- customer ----------------
customer_urls = ([
    path("dashboard/", v.CustomerDashboardView.as_view(), name="dashboard"),
    path("shipments/", v.CustomerShipmentsView.as_view(), name="shipments"),
    path("shipments/new/", v.NewShipmentView.as_view(), name="new_shipment"),
    path("complaints/new/", v.NewComplaintView.as_view(), name="new_complaint"),
] + build(C, [
    ("shipments/<int:pk>/", "shipment_detail", "customer/shipments.html"),
    ("tracking/", "track", "customer/tracking.html"),
    ("complaints/", "complaints", "customer/complaints.html"),
    ("complaints/<int:pk>/", "complaint_detail", "customer/complaints.html"),
    ("payments/", "payments", "customer/payments.html"),
]), "customer")

# ---------------- driver ----------------
driver_urls = ([
    path("dashboard/", dv.DriverDashboardView.as_view(), name="dashboard"),
    path("deliveries/", dv.DriverDeliveriesView.as_view(), name="deliveries"),
    path("deliveries/<int:pk>/", dv.DriverDeliveryDetailView.as_view(), name="delivery_detail"),
    path("deliveries/<int:pk>/accept/", dv.accept_delivery, name="accept_delivery"),
    path("deliveries/<int:pk>/status/", dv.update_delivery_status, name="update_delivery_status"),
    path("history/", dv.DriverHistoryView.as_view(), name="history"),
] + build(D, [
    ("availability/", "availability", "driver/availability.html"),
    ("location/", "location", "driver/location.html"),
]) + [path("profile/", v.ProfileView.as_view(), name="profile")], "driver")

# ---------------- manager ----------------
manager_rows = (
    crud("customers", "customer", "manager/customers.html", create=False)
    + crud("drivers", "driver", "manager/drivers.html", "manager/drivers_details.html", create=False)
    + crud("users", "user", "manager/users.html")
    + crud("warehouses", "warehouse", "manager/warehouses.html")
    + [
        ("dashboard/", "dashboard", "manager/dashboard.html"),
        ("shipments/", "shipments", "manager/shipments.html"),
        ("shipments/list/", "shipment_list", "manager/shipments.html"),
        ("shipments/new/", "shipment_create", "manager/shipments.html"),
        ("shipments/bulk/", "shipment_bulk_action", None),
        ("shipments/<int:pk>/", "shipment_detail", "manager/shipments_details.html"),
        ("shipments/<int:pk>/assign/", "shipment_assign", None),
        ("shipments/<int:pk>/reassign/", "shipment_reassign", None),
        ("shipments/<int:pk>/status/", "shipment_update_status", None),
        ("shipments/<int:pk>/investigate/", "shipment_investigate", None),
        ("delayed/", "delayed_deliveries", "manager/delayed.html"),
        ("customers/<int:pk>/shipments/", "customer_shipments", "manager/shipments.html"),
        ("drivers/<int:pk>/assignments/", "driver_assignments", "manager/drivers.html"),
        ("drivers/<int:pk>/location/", "driver_location", "manager/drivers_details.html"),
        ("drivers/<int:pk>/availability/", "driver_availability", None),
        ("drivers/<int:pk>/assign/", "driver_assign_shipment", None),
        ("assignments/", "assignments", "manager/drivers.html"),
        ("complaints/", "complaints", "manager/complaints.html"),
        ("analytics/", "analytics", "manager/analytics.html"),
        ("audit-logs/", "audit_logs", "manager/audit_logs.html"),
        ("ai-actions/", "ai_actions", "manager/ai_actions.html"),
        ("ai-assistant/", "ai_assistant", "manager/ai_assistant.html"),
        ("notifications/", "notifications", "manager/notifications.html"),
        ("notifications/read-all/", "notification_mark_all_read", None),
        ("notifications/<int:pk>/read/", "notification_mark_read", None),
        ("notifications/<int:pk>/unread/", "notification_mark_unread", None),
        ("notifications/<int:pk>/delete/", "notification_delete", None),
        ("settings/", "settings", "manager/setting.html"),
        ("settings/sessions/revoke/", "sessions_revoke", None),
        ("settings/two-factor/", "two_factor", None),
    ]
)
# Routes that now have a real view (they'd otherwise fall through to a static page).
MANAGER_REAL_VIEWS = {
    "dashboard", "customers", "customer_activate", "customer_deactivate",
    "drivers", "driver_activate", "driver_deactivate", "assignments",
    "shipments", "shipment_list", "shipment_create", "shipment_bulk_action",
    "shipment_detail", "shipment_assign", "shipment_reassign", "shipment_update_status",
}

manager_real = [
    path("dashboard/", mv.ManagerDashboardView.as_view(), name="dashboard"),
    path("customers/", mv.ManagerCustomersView.as_view(), name="customers"),
    path("customers/<int:pk>/activate/", mv.user_set_active,
         {"role": "CUSTOMER", "active": True}, name="customer_activate"),
    path("customers/<int:pk>/deactivate/", mv.user_set_active,
         {"role": "CUSTOMER", "active": False}, name="customer_deactivate"),
    path("drivers/", mv.ManagerDriversView.as_view(), name="drivers"),
    path("drivers/<int:pk>/activate/", mv.user_set_active,
         {"role": "DRIVER", "active": True}, name="driver_activate"),
    path("drivers/<int:pk>/deactivate/", mv.user_set_active,
         {"role": "DRIVER", "active": False}, name="driver_deactivate"),
    path("assignments/", mv.ManagerDriversView.as_view(), name="assignments"),
    path("shipments/", mv.ManagerShipmentsView.as_view(), name="shipments"),
    path("shipments/list/", mv.ManagerShipmentsView.as_view(), name="shipment_list"),
    path("shipments/new/", mv.ManagerShipmentsView.as_view(), name="shipment_create"),
    path("shipments/bulk/", mv.shipment_bulk_action, name="shipment_bulk_action"),
    path("shipments/<int:pk>/", mv.ManagerShipmentDetailView.as_view(), name="shipment_detail"),
    path("shipments/<int:pk>/assign/", mv.shipment_assign, name="shipment_assign"),
    path("shipments/<int:pk>/reassign/", mv.shipment_assign, name="shipment_reassign"),
    path("shipments/<int:pk>/status/", mv.shipment_update_status, name="shipment_update_status"),
]
manager_pages = build(M, [r for r in manager_rows if r[1] not in MANAGER_REAL_VIEWS])

manager_urls = (manager_real + manager_pages + [
    path("payments/", RedirectView.as_view(pattern_name="manager:dashboard"), name="payments"),
    path("profile/", v.ProfileView.as_view(), name="profile"),
    path("settings/password/", v.PasswordChangePage.as_view(), name="password_change"),
], "manager")

# ---------------- notifications ----------------
notifications_urls = ([
    path("", notif_view, name="list"),
    path("read-all/", action_stub, name="mark_all_read"),
    path("<int:pk>/read/", action_stub, name="mark_read"),
], "notifications")

# ---------------- placeholders لروابط الفوتر ----------------
legal_urls = ([
    path("terms/", RedirectView.as_view(url="/"), name="terms"),
    path("privacy/", RedirectView.as_view(url="/"), name="privacy"),
], "legal")
support_urls = ([
    path("contact/", RedirectView.as_view(url="/"), name="contact"),
    path("faq/", RedirectView.as_view(url="/"), name="faq"),
], "support")

urlpatterns = [
    path("", TemplateView.as_view(template_name="landingpage/home.html"), name="home"),
    path("login/", v.LoginView.as_view(), name="login"),
    path("signup/", v.RegisterView.as_view(), name="signup"),
    path("tracking/", page("customer/tracking.html", C), name="tracking"),
    path("ai-assistant/", page("manager/ai_assistant.html"), name="ai_assistant"),
    path("accounts/", include(accounts_urls)),
    path("customer/", include(customer_urls)),
    path("driver/", include(driver_urls)),
    path("manager/", include(manager_urls)),
    path("notifications/", include(notifications_urls)),
    path("legal/", include(legal_urls)),
    path("support/", include(support_urls)),
]