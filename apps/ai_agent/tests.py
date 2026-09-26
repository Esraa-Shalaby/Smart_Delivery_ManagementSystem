
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.ai_agent.models import AIAction
from apps.ai_agent.tools import execute_tool
from apps.drivers.services import create_or_update_driver_profile, update_driver_availability
from apps.shipments.services import assign_driver, create_shipment

SHIPMENT_DATA = dict(
    pickup_address="1 Warehouse Rd",
    delivery_address="2 Customer St",
    package_description="Books",
    package_weight=Decimal("2.50"),
    delivery_fee=Decimal("50.00"),
)


def make_user(username, role, **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="strongpass123",
        role=role,
        **extra,
    )


class ToolPermissionTests(TestCase):
    """Role-based access and data isolation at the tool-execution layer."""

    def setUp(self):
        self.customer = make_user("cust1", User.Role.CUSTOMER)
        self.other_customer = make_user("cust2", User.Role.CUSTOMER)
        self.driver = make_user("drv1", User.Role.DRIVER)
        self.manager = make_user("mgr1", User.Role.MANAGER)
        create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC1")
        self.shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)

    def test_customer_can_check_own_shipment_status(self):
        outcome = execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=self.customer,
        )
        self.assertTrue(outcome["success"])
        self.assertEqual(outcome["data"]["tracking_number"], self.shipment.tracking_number)

    def test_customer_cannot_check_others_shipment_status(self):
        outcome = execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=self.other_customer,
        )
        self.assertFalse(outcome["success"])

    def test_customer_cannot_use_manager_only_tool(self):
        outcome = execute_tool(tool_name="get_available_drivers", params={}, user=self.customer)
        self.assertFalse(outcome["success"])

    def test_customer_cannot_assign_driver(self):
        outcome = execute_tool(
            tool_name="assign_driver",
            params={"shipment_id": self.shipment.id, "driver_id": self.driver.id},
            user=self.customer,
        )
        self.assertFalse(outcome["success"])

    def test_manager_can_assign_driver(self):
        outcome = execute_tool(
            tool_name="assign_driver",
            params={"shipment_id": self.shipment.id, "driver_id": self.driver.id},
            user=self.manager,
        )
        self.assertTrue(outcome["success"])
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, "ASSIGNED")

    def test_manager_can_list_available_drivers(self):
        update_driver_availability(driver_profile=self.driver.driver_profile, is_available=True)
        outcome = execute_tool(tool_name="get_available_drivers", params={}, user=self.manager)
        self.assertTrue(outcome["success"])
        self.assertEqual(outcome["data"]["count"], 1)

    def test_driver_can_access_assigned_shipment_status(self):
        assign_driver(shipment=self.shipment, driver=self.driver, assigned_by=self.manager)
        outcome = execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=self.driver,
        )
        self.assertTrue(outcome["success"])

    def test_driver_cannot_access_unassigned_shipment_status(self):
        outcome = execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=self.driver,
        )
        self.assertFalse(outcome["success"])

    def test_driver_can_view_own_driver_details(self):
        outcome = execute_tool(tool_name="get_driver_details", params={}, user=self.driver)
        self.assertTrue(outcome["success"])

    def test_driver_cannot_view_another_drivers_details(self):
        other_driver = make_user("drv2", User.Role.DRIVER)
        other_profile = create_or_update_driver_profile(
            user=other_driver, phone="0111111111", license_number="LIC2"
        )
        outcome = execute_tool(
            tool_name="get_driver_details",
            params={"driver_profile_id": other_profile.id},
            user=self.driver,
        )
        self.assertFalse(outcome["success"])

    def test_customer_gets_only_own_shipments_list(self):
        create_shipment(customer=self.other_customer, **SHIPMENT_DATA)
        outcome = execute_tool(tool_name="get_customer_shipments", params={}, user=self.customer)
        self.assertTrue(outcome["success"])
        self.assertEqual(outcome["data"]["count"], 1)

    def test_driver_cannot_use_get_customer_shipments_tool(self):
        outcome = execute_tool(tool_name="get_customer_shipments", params={}, user=self.driver)
        self.assertFalse(outcome["success"])

    def test_unrecognized_tool_fails_gracefully(self):
        outcome = execute_tool(tool_name="drop_database", params={}, user=self.manager)
        self.assertFalse(outcome["success"])


class AIActionLoggingTests(TestCase):
    """Every tool call, successful or not, is recorded — with no secrets."""

    def setUp(self):
        self.customer = make_user("custlog", User.Role.CUSTOMER)
        self.shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)

    def test_successful_call_is_logged(self):
        execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=self.customer,
        )
        log = AIAction.objects.filter(action="get_delivery_status", success=True).latest("created_at")
        self.assertEqual(log.user, self.customer)

    def test_failed_call_is_logged(self):
        other_customer = make_user("custlog2", User.Role.CUSTOMER)
        execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=other_customer,
        )
        log = AIAction.objects.filter(action="get_delivery_status", success=False).latest("created_at")
        self.assertEqual(log.user, other_customer)

    def test_log_never_stores_password_field(self):
        execute_tool(
            tool_name="get_delivery_status",
            params={"shipment_id": self.shipment.id},
            user=self.customer,
        )
        log = AIAction.objects.latest("created_at")
        self.assertNotIn("password", log.result.lower())
        self.assertNotIn("password", log.input.lower())


class ChatbotAPITests(APITestCase):
    """The chatbot HTTP endpoint end-to-end."""

    def setUp(self):
        self.customer = make_user("custapi", User.Role.CUSTOMER)
        self.manager = make_user("mgrapi", User.Role.MANAGER)
        self.shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        self.url = reverse("ai_agent:chat")

    def test_unauthenticated_request_rejected(self):
        response = self.client.post(self.url, {"message": "track my order"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_can_ask_about_own_shipment(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            self.url,
            {"message": "status", "params": {"shipment_id": self.shipment.id}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_empty_message_rejected(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(self.url, {"message": "  "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_can_request_delayed_deliveries(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.url, {"message": "show me delayed deliveries"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])