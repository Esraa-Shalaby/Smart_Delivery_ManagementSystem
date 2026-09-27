

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments import services
from apps.payments.models import Payment

User = get_user_model()


def _make_user(username, role, **extra):
    defaults = {"email": f"{username}@example.com", "password": "pass12345"}
    defaults.update(extra)
    user = User.objects.create_user(username=username, **defaults)
    if hasattr(user, "role"):
        user.role = role
        user.save(update_fields=["role"])
    return user


def _make_shipment(customer):
    from apps.shipments.models import Shipment

    try:
        return Shipment.objects.create(customer=customer)
    except TypeError:
        return Shipment.objects.create()


class PaymentModelAndServiceTests(TestCase):
    def setUp(self):
        self.customer = _make_user("customer1", "CUSTOMER")
        self.shipment = _make_shipment(self.customer)

    def test_create_payment_success(self):
        payment = services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("100.00"),
            payment_method=Payment.PaymentMethod.CASH,
        )
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(payment.customer, self.customer)
        self.assertEqual(payment.shipment, self.shipment)

    def test_negative_amount_rejected_by_service(self):
        with self.assertRaises(services.PaymentError):
            services.create_payment(
                shipment=self.shipment,
                customer=self.customer,
                amount=Decimal("-1.00"),
                payment_method=Payment.PaymentMethod.CASH,
            )

    def test_negative_amount_rejected_by_model_validation(self):
        payment = Payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("-5.00"),
            payment_method=Payment.PaymentMethod.CASH,
        )
        with self.assertRaises(Exception):
            payment.save()

    def test_duplicate_transaction_reference_rejected(self):
        services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("10.00"),
            payment_method=Payment.PaymentMethod.ONLINE,
            transaction_reference="TXN-1",
        )
        with self.assertRaises(services.PaymentError):
            services.create_payment(
                shipment=self.shipment,
                customer=self.customer,
                amount=Decimal("20.00"),
                payment_method=Payment.PaymentMethod.ONLINE,
                transaction_reference="TXN-1",
            )

    def test_multiple_payments_without_reference_are_allowed(self):
        services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("10.00"),
            payment_method=Payment.PaymentMethod.CASH,
        )
        # No transaction_reference on either -> should not collide.
        services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("15.00"),
            payment_method=Payment.PaymentMethod.CASH,
        )
        self.assertEqual(Payment.objects.count(), 2)

    def test_mark_payment_as_paid(self):
        payment = services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("50.00"),
            payment_method=Payment.PaymentMethod.CARD,
        )
        payment = services.mark_payment_as_paid(payment, transaction_reference="TXN-2")
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(payment.transaction_reference, "TXN-2")

    def test_refund_requires_paid_status(self):
        payment = services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("50.00"),
            payment_method=Payment.PaymentMethod.CARD,
        )
        with self.assertRaises(services.PaymentError):
            services.refund_payment(payment)

    def test_refund_after_paid_succeeds(self):
        payment = services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("50.00"),
            payment_method=Payment.PaymentMethod.CARD,
        )
        payment = services.mark_payment_as_paid(payment)
        payment = services.refund_payment(payment)
        self.assertEqual(payment.status, Payment.PaymentStatus.REFUNDED)

    def test_cannot_transition_out_of_refunded(self):
        payment = services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("50.00"),
            payment_method=Payment.PaymentMethod.CARD,
        )
        payment = services.mark_payment_as_paid(payment)
        payment = services.refund_payment(payment)
        with self.assertRaises(services.PaymentError):
            services.process_payment_status(payment, Payment.PaymentStatus.PENDING)

    def test_get_customer_payment_history(self):
        services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("10.00"),
            payment_method=Payment.PaymentMethod.CASH,
        )
        other_customer = _make_user("customer2", "CUSTOMER")
        other_shipment = _make_shipment(other_customer)
        services.create_payment(
            shipment=other_shipment,
            customer=other_customer,
            amount=Decimal("30.00"),
            payment_method=Payment.PaymentMethod.CASH,
        )
        history = services.get_customer_payment_history(self.customer)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().customer, self.customer)

    def test_get_payment_details_not_found(self):
        with self.assertRaises(services.PaymentError):
            services.get_payment_details(999999)


class PaymentAPITests(APITestCase):
    def setUp(self):
        self.customer = _make_user("cust_api1", "CUSTOMER")
        self.other_customer = _make_user("cust_api2", "CUSTOMER")
        self.driver = _make_user("driver_api1", "DRIVER")
        self.manager = _make_user("manager_api1", "MANAGER")

        self.shipment = _make_shipment(self.customer)
        self.payment = services.create_payment(
            shipment=self.shipment,
            customer=self.customer,
            amount=Decimal("75.00"),
            payment_method=Payment.PaymentMethod.ONLINE,
        )

    def test_customer_can_list_own_payments_only(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        ids = [row["id"] for row in data]
        self.assertIn(self.payment.id, ids)

    def test_customer_cannot_view_other_customers_payment(self):
        self.client.force_authenticate(self.other_customer)
        response = self.client.get(reverse("payment-detail", args=[self.payment.id]))
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_driver_has_no_access(self):
        self.client.force_authenticate(self.driver)
        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_view_all_payments(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_can_create_own_payment(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("payment-list"),
            {
                "shipment": self.shipment.id,
                "amount": "20.00",
                "payment_method": Payment.PaymentMethod.CASH,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["customer"], self.customer.id)

    def test_create_payment_negative_amount_rejected_via_api(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("payment-list"),
            {
                "shipment": self.shipment.id,
                "amount": "-5.00",
                "payment_method": Payment.PaymentMethod.CASH,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_cannot_create_payment(self):
        self.client.force_authenticate(self.driver)
        response = self.client.post(
            reverse("payment-list"),
            {
                "shipment": self.shipment.id,
                "amount": "20.00",
                "payment_method": Payment.PaymentMethod.CASH,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_mark_paid(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("payment-mark-paid", args=[self.payment.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_mark_paid(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(reverse("payment-mark-paid", args=[self.payment.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PAID)

    def test_manager_can_refund_paid_payment(self):
        services.mark_payment_as_paid(self.payment)
        self.client.force_authenticate(self.manager)
        response = self.client.post(reverse("payment-refund", args=[self.payment.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.REFUNDED)

    def test_customer_cannot_refund(self):
        services.mark_payment_as_paid(self.payment)
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("payment-refund", args=[self.payment.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_history_endpoint_returns_own_payments(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("payment-history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)