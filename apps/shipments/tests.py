"""
Tests for the shipments app.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.shipments.models import DeliveryAssignment, Shipment, ShipmentStatusHistory
from apps.shipments.services import (
    assign_driver,
    create_shipment,
    reassign_driver,
    update_shipment_status,
)

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


class ShipmentServiceTests(TestCase):
    """Business logic in shipments/services.py."""

    def setUp(self):
        self.customer = make_user("cust1", User.Role.CUSTOMER)
        self.driver = make_user("drv1", User.Role.DRIVER)
        self.driver2 = make_user("drv2", User.Role.DRIVER)
        self.manager = make_user("mgr1", User.Role.MANAGER)

    def test_create_shipment_success(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        self.assertEqual(shipment.customer, self.customer)
        self.assertEqual(shipment.status, Shipment.Status.PENDING)
        self.assertTrue(ShipmentStatusHistory.objects.filter(shipment=shipment).exists())

    def test_create_shipment_rejects_non_customer(self):
        with self.assertRaises(ValidationError):
            create_shipment(customer=self.driver, **SHIPMENT_DATA)

    def test_tracking_number_is_unique(self):
        s1 = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        s2 = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        self.assertNotEqual(s1.tracking_number, s2.tracking_number)

    def test_assign_driver_success(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        assignment = assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)
        shipment.refresh_from_db()
        self.assertEqual(assignment.driver, self.driver)
        self.assertTrue(assignment.is_active)
        self.assertEqual(shipment.status, Shipment.Status.ASSIGNED)

    def test_assign_driver_rejects_non_driver_role(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        with self.assertRaises(ValidationError):
            assign_driver(shipment=shipment, driver=self.customer, assigned_by=self.manager)

    def test_assign_driver_twice_requires_reassign(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)
        with self.assertRaises(ValidationError):
            assign_driver(shipment=shipment, driver=self.driver2, assigned_by=self.manager)

    def test_reassign_driver_keeps_history(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        first = assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)
        second = reassign_driver(shipment=shipment, new_driver=self.driver2, assigned_by=self.manager)

        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(DeliveryAssignment.objects.filter(shipment=shipment).count(), 2)

    def test_update_status_valid_transition(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)
        updated = update_shipment_status(
            shipment=shipment, new_status=Shipment.Status.PICKED_UP, changed_by=self.driver
        )
        self.assertEqual(updated.status, Shipment.Status.PICKED_UP)

    def test_update_status_invalid_transition_rejected(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        with self.assertRaises(ValidationError):
            update_shipment_status(
                shipment=shipment, new_status=Shipment.Status.DELIVERED, changed_by=self.manager
            )

    def test_status_history_recorded_on_each_change(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)
        update_shipment_status(
            shipment=shipment, new_status=Shipment.Status.PICKED_UP, changed_by=self.driver
        )
        # created + assigned + picked_up
        self.assertEqual(ShipmentStatusHistory.objects.filter(shipment=shipment).count(), 3)


class ShipmentAPITests(APITestCase):
    """Endpoint behavior, ownership and role-based permissions."""

    def setUp(self):
        self.customer = make_user("custapi", User.Role.CUSTOMER)
        self.other_customer = make_user("custapi2", User.Role.CUSTOMER)
        self.driver = make_user("drvapi", User.Role.DRIVER)
        self.manager = make_user("mgrapi", User.Role.MANAGER)
        self.list_create_url = reverse("shipments:shipment-list-create")

    def test_customer_can_create_shipment(self):
        self.client.force_authenticate(user=self.customer)
        payload = {k: str(v) for k, v in SHIPMENT_DATA.items()}
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Shipment.Status.PENDING)

    def test_driver_cannot_create_shipment(self):
        self.client.force_authenticate(user=self.driver)
        payload = {k: str(v) for k, v in SHIPMENT_DATA.items()}
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_sees_only_own_shipments(self):
        create_shipment(customer=self.customer, **SHIPMENT_DATA)
        create_shipment(customer=self.other_customer, **SHIPMENT_DATA)

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_customer_cannot_view_others_shipment_detail(self):
        shipment = create_shipment(customer=self.other_customer, **SHIPMENT_DATA)
        self.client.force_authenticate(user=self.customer)
        url = reverse("shipments:shipment-detail", args=[shipment.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_assign_driver(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        self.client.force_authenticate(user=self.manager)
        url = reverse("shipments:shipment-assign", args=[shipment.pk])
        response = self.client.post(url, {"driver": self.driver.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_customer_cannot_assign_driver(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        self.client.force_authenticate(user=self.customer)
        url = reverse("shipments:shipment-assign", args=[shipment.pk])
        response = self.client.post(url, {"driver": self.driver.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_driver_can_update_status(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)

        self.client.force_authenticate(user=self.driver)
        url = reverse("shipments:shipment-status-update", args=[shipment.pk])
        response = self.client.patch(url, {"status": Shipment.Status.PICKED_UP})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Shipment.Status.PICKED_UP)

    def test_unassigned_driver_cannot_update_status(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        other_driver = make_user("otherdrv", User.Role.DRIVER)
        assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)

        self.client.force_authenticate(user=other_driver)
        url = reverse("shipments:shipment-status-update", args=[shipment.pk])
        response = self.client.patch(url, {"status": Shipment.Status.PICKED_UP})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tracking_endpoint_returns_history(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        self.client.force_authenticate(user=self.customer)
        url = reverse("shipments:shipment-tracking", args=[shipment.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["status_history"]), 1)

    def test_unauthenticated_access_rejected(self):
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)