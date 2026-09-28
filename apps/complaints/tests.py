 

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.complaints.models import Complaint
from apps.complaints.services import (
    create_complaint,
    list_all_complaints,
    list_customer_complaints,
    resolve_complaint,
    respond_to_complaint,
    update_complaint_status,
)
from apps.shipments.services import create_shipment

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


class ComplaintServiceTests(TestCase):
    """Business logic in complaints/services.py."""

    def setUp(self):
        self.customer = make_user("cust1", User.Role.CUSTOMER)
        self.other_customer = make_user("cust2", User.Role.CUSTOMER)
        self.driver = make_user("drv1", User.Role.DRIVER)
        self.manager = make_user("mgr1", User.Role.MANAGER)
        self.shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)

    def test_create_complaint_success(self):
        complaint = create_complaint(
            customer=self.customer, subject="Late delivery", description="It was late.",
        )
        self.assertEqual(complaint.status, Complaint.Status.OPEN)
        self.assertEqual(complaint.priority, Complaint.Priority.MEDIUM)

    def test_create_complaint_rejects_non_customer(self):
        with self.assertRaises(ValidationError):
            create_complaint(customer=self.driver, subject="X", description="Y")

    def test_create_complaint_rejects_others_shipment(self):
        with self.assertRaises(ValidationError):
            create_complaint(
                customer=self.other_customer,
                subject="X",
                description="Y",
                shipment=self.shipment,
            )

    def test_create_complaint_with_own_shipment_succeeds(self):
        complaint = create_complaint(
            customer=self.customer, subject="Damaged", description="Box was crushed.",
            shipment=self.shipment,
        )
        self.assertEqual(complaint.shipment, self.shipment)

    def test_respond_moves_open_to_in_progress(self):
        complaint = create_complaint(customer=self.customer, subject="X", description="Y")
        updated = respond_to_complaint(
            complaint=complaint, response="We're looking into it.", responded_by=self.manager
        )
        self.assertEqual(updated.status, Complaint.Status.IN_PROGRESS)
        self.assertEqual(updated.response, "We're looking into it.")

    def test_update_status_valid_transition(self):
        complaint = create_complaint(customer=self.customer, subject="X", description="Y")
        updated = update_complaint_status(
            complaint=complaint, new_status=Complaint.Status.IN_PROGRESS, changed_by=self.manager
        )
        self.assertEqual(updated.status, Complaint.Status.IN_PROGRESS)

    def test_update_status_invalid_transition_rejected(self):
        complaint = create_complaint(customer=self.customer, subject="X", description="Y")
        with self.assertRaises(ValidationError):
            update_complaint_status(
                complaint=complaint, new_status=Complaint.Status.RESOLVED, changed_by=self.manager
            )

    def test_resolve_complaint_sets_resolver_and_timestamp(self):
        complaint = create_complaint(customer=self.customer, subject="X", description="Y")
        update_complaint_status(
            complaint=complaint, new_status=Complaint.Status.IN_PROGRESS, changed_by=self.manager
        )
        resolved = resolve_complaint(complaint=complaint, resolved_by=self.manager, response="Refunded.")
        self.assertEqual(resolved.status, Complaint.Status.RESOLVED)
        self.assertEqual(resolved.resolved_by, self.manager)
        self.assertIsNotNone(resolved.resolved_at)
        self.assertEqual(resolved.response, "Refunded.")

    def test_resolve_closed_complaint_rejected(self):
        complaint = create_complaint(customer=self.customer, subject="X", description="Y")
        update_complaint_status(
            complaint=complaint, new_status=Complaint.Status.CLOSED, changed_by=self.manager
        )
        with self.assertRaises(ValidationError):
            resolve_complaint(complaint=complaint, resolved_by=self.manager)

    def test_list_customer_complaints_scoped(self):
        create_complaint(customer=self.customer, subject="A", description="A")
        create_complaint(customer=self.other_customer, subject="B", description="B")
        self.assertEqual(list_customer_complaints(customer=self.customer).count(), 1)

    def test_list_all_complaints_returns_everything(self):
        create_complaint(customer=self.customer, subject="A", description="A")
        create_complaint(customer=self.other_customer, subject="B", description="B")
        self.assertEqual(list_all_complaints().count(), 2)


class ComplaintAPITests(APITestCase):
    """Endpoint behavior, ownership, and role-based permissions."""

    def setUp(self):
        self.customer = make_user("custapi", User.Role.CUSTOMER)
        self.other_customer = make_user("custapi2", User.Role.CUSTOMER)
        self.driver = make_user("drvapi", User.Role.DRIVER)
        self.manager = make_user("mgrapi", User.Role.MANAGER)
        self.list_create_url = reverse("complaints:complaint-list-create")

    def test_customer_can_create_complaint(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            self.list_create_url, {"subject": "Late", "description": "Very late.", "priority": "HIGH"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Complaint.Status.OPEN)

    def test_driver_cannot_create_complaint(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.post(
            self.list_create_url, {"subject": "X", "description": "Y"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_list_complaints(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_sees_only_own_complaints(self):
        create_complaint(customer=self.customer, subject="A", description="A")
        create_complaint(customer=self.other_customer, subject="B", description="B")

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_manager_sees_all_complaints(self):
        create_complaint(customer=self.customer, subject="A", description="A")
        create_complaint(customer=self.other_customer, subject="B", description="B")

        self.client.force_authenticate(user=self.manager)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_customer_cannot_view_others_complaint_detail(self):
        complaint = create_complaint(customer=self.other_customer, subject="A", description="A")
        self.client.force_authenticate(user=self.customer)
        url = reverse("complaints:complaint-detail", args=[complaint.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_respond_to_complaint(self):
        complaint = create_complaint(customer=self.customer, subject="A", description="A")
        self.client.force_authenticate(user=self.manager)
        url = reverse("complaints:complaint-respond", args=[complaint.pk])
        response = self.client.post(url, {"response": "We're on it."})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Complaint.Status.IN_PROGRESS)

    def test_customer_cannot_respond_to_complaint(self):
        complaint = create_complaint(customer=self.customer, subject="A", description="A")
        self.client.force_authenticate(user=self.customer)
        url = reverse("complaints:complaint-respond", args=[complaint.pk])
        response = self.client.post(url, {"response": "Trying to self-respond."})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_update_status(self):
        complaint = create_complaint(customer=self.customer, subject="A", description="A")
        self.client.force_authenticate(user=self.driver)
        url = reverse("complaints:complaint-status-update", args=[complaint.pk])
        response = self.client.patch(url, {"status": Complaint.Status.IN_PROGRESS})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_resolve_complaint(self):
        complaint = create_complaint(customer=self.customer, subject="A", description="A")
        self.client.force_authenticate(user=self.manager)
        self.client.patch(
            reverse("complaints:complaint-status-update", args=[complaint.pk]),
            {"status": Complaint.Status.IN_PROGRESS},
        )
        url = reverse("complaints:complaint-resolve", args=[complaint.pk])
        response = self.client.post(url, {"response": "Refund issued."})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Complaint.Status.RESOLVED)

    def test_unauthenticated_access_rejected(self):
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)