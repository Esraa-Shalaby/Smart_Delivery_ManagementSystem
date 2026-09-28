from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, APISimpleTestCase, force_authenticate

from . import services, views

 
VIEW_TO_SERVICE = {
    views.ShipmentStatisticsView: "get_shipment_statistics",
    views.DriverStatisticsView: "get_driver_statistics",
    views.PaymentStatisticsView: "get_payment_statistics",
    views.ComplaintStatisticsView: "get_complaint_statistics",
    views.DashboardSummaryView: "get_dashboard_summary",
}


def call(view, user=None):
    request = APIRequestFactory().get("/")
    if user is not None:
        force_authenticate(request, user=user)
    return view.as_view()(request)


class AnalyticsPermissionTests(APISimpleTestCase):
    def test_anonymous_is_rejected(self):
        for view in VIEW_TO_SERVICE:
            with self.subTest(view=view.__name__):
                self.assertIn(call(view).status_code, (401, 403))

    def test_non_manager_is_forbidden(self):
        for role in ("CUSTOMER", "DRIVER", "ADMIN", None):
            user = SimpleNamespace(is_authenticated=True, role=role)
            for view in VIEW_TO_SERVICE:
                with self.subTest(view=view.__name__, role=role):
                    self.assertEqual(call(view, user).status_code, 403)

    def test_manager_gets_json_payload(self):
        manager = SimpleNamespace(is_authenticated=True, role="MANAGER")
        for view, service_name in VIEW_TO_SERVICE.items():
            with self.subTest(view=view.__name__):
                with mock.patch.object(
                    services, service_name, return_value={"ok": True}
                ) as patched:
                    response = call(view, manager)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, {"ok": True})
                patched.assert_called_once()



REQUIRED = {"SHIPMENT": {}, "DRIVER": {}, "PAYMENT": {}, "COMPLAINT": {}}


def create(section, **fields):
    return services._model(section).objects.create(**{**REQUIRED[section], **fields})


class ShipmentStatisticsTests(TestCase):
    def test_counts_and_delayed(self):
        cfg = services.get_config()["SHIPMENT"]
        status, eta = cfg["status_field"], cfg["eta_field"]
        past = timezone.now() - timedelta(days=1)
        future = timezone.now() + timedelta(days=1)

        create("SHIPMENT", **{status: "PENDING"})
        create("SHIPMENT", **{status: "PENDING"})
        create("SHIPMENT", **{status: "DELIVERED", eta: past})  # late but closed
        create("SHIPMENT", **{status: "CANCELLED"})
        create("SHIPMENT", **{status: "IN_TRANSIT", eta: past})  # overdue -> delayed
        create("SHIPMENT", **{status: "IN_TRANSIT", eta: future})

        with self.assertNumQueries(2):
            stats = services.get_shipment_statistics()

        self.assertEqual(stats["total_shipments"], 6)
        self.assertEqual(stats["pending_shipments"], 2)
        self.assertEqual(stats["delivered_shipments"], 1)
        self.assertEqual(stats["cancelled_shipments"], 1)
        self.assertEqual(stats["delayed_shipments"], 1)
        self.assertEqual(stats["shipments_by_status"]["IN_TRANSIT"], 2)


class DriverStatisticsTests(TestCase):
    def test_availability_and_delivery_counts(self):
        avail = services.get_config()["DRIVER"]["available_field"]
        ship = services.get_config()["SHIPMENT"]
        busy = create("DRIVER", **{avail: False})
        free = create("DRIVER", **{avail: True})
        for _ in range(2):
            create("SHIPMENT", **{ship["driver_field"]: free, ship["status_field"]: "DELIVERED"})
        create("SHIPMENT", **{ship["driver_field"]: busy, ship["status_field"]: "IN_TRANSIT"})

        stats = services.get_driver_statistics()

        self.assertEqual(stats["total_drivers"], 2)
        self.assertEqual(stats["available_drivers"], 1)
        self.assertEqual(stats["unavailable_drivers"], 1)
        top = stats["deliveries_per_driver"][0]
        self.assertEqual((top["driver_id"], top["delivered_shipments"]), (free.pk, 2))
        self.assertEqual(stats["deliveries_per_driver"][1]["delivered_shipments"], 0)


class PaymentStatisticsTests(TestCase):
    def test_amounts_and_counts(self):
        cfg = services.get_config()["PAYMENT"]
        status, amount = cfg["status_field"], cfg["amount_field"]
        create("PAYMENT", **{status: "PAID", amount: Decimal("100.00")})
        create("PAYMENT", **{status: "PAID", amount: Decimal("50.50")})
        create("PAYMENT", **{status: "PENDING", amount: Decimal("20.00")})
        create("PAYMENT", **{status: "FAILED", amount: Decimal("75.00")})

        with self.assertNumQueries(1):
            stats = services.get_payment_statistics()

        self.assertEqual(stats["total_payments"], 4)
        self.assertEqual(stats["failed_payments"], 1)
        self.assertEqual(stats["paid_amount"], Decimal("150.50"))
        self.assertEqual(stats["pending_amount"], Decimal("20.00"))

    def test_empty_table_returns_zero_amounts(self):
        stats = services.get_payment_statistics()
        self.assertEqual(stats["paid_amount"], Decimal("0.00"))
        self.assertEqual(stats["pending_amount"], Decimal("0.00"))


class ComplaintStatisticsTests(TestCase):
    def test_status_and_priority_breakdown(self):
        cfg = services.get_config()["COMPLAINT"]
        status, priority = cfg["status_field"], cfg["priority_field"]
        create("COMPLAINT", **{status: "OPEN", priority: "HIGH"})
        create("COMPLAINT", **{status: "IN_PROGRESS", priority: "HIGH"})
        create("COMPLAINT", **{status: "RESOLVED", priority: "LOW"})

        with self.assertNumQueries(2):
            stats = services.get_complaint_statistics()

        self.assertEqual(stats["total_complaints"], 3)
        self.assertEqual(stats["open_complaints"], 2)
        self.assertEqual(stats["resolved_complaints"], 1)
        self.assertEqual(stats["complaints_by_priority"], {"HIGH": 2, "LOW": 1})


class DashboardSummaryTests(TestCase):
    def test_contains_all_sections(self):
        summary = services.get_dashboard_summary()
        self.assertEqual(
            set(summary),
            {"generated_at", "shipments", "drivers", "payments", "complaints"},
        )