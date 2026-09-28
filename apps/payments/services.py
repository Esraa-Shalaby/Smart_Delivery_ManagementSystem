

from django.db import transaction
from django.utils import timezone

from .models import Payment


class PaymentError(Exception):
    """Raised for payment validation problems."""


VALID_STATUS_TRANSITIONS = {
    Payment.PaymentStatus.PENDING: {
        Payment.PaymentStatus.PAID,
        Payment.PaymentStatus.FAILED,
        Payment.PaymentStatus.CANCELLED,
    },
    Payment.PaymentStatus.PAID: {
        Payment.PaymentStatus.REFUNDED,
    },
    Payment.PaymentStatus.FAILED: {
        Payment.PaymentStatus.PENDING,
        Payment.PaymentStatus.CANCELLED,
    },
    Payment.PaymentStatus.REFUNDED: set(),
    Payment.PaymentStatus.CANCELLED: set(),
}


def _ensure_unique_reference(transaction_reference, *, exclude_pk=None):
    if not transaction_reference:
        return
    qs = Payment.objects.filter(transaction_reference=transaction_reference)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise PaymentError("transaction_reference must be unique.")


@transaction.atomic
def create_payment(*, shipment, customer, amount, payment_method,
                    transaction_reference=None, status=None):
    if shipment is None:
        raise PaymentError("Payment must belong to a shipment.")
    if customer is None:
        raise PaymentError("Payment must belong to a customer.")
    if amount is None or amount < 0:
        raise PaymentError("Amount cannot be negative.")

    _ensure_unique_reference(transaction_reference)

    payment = Payment(
        shipment=shipment,
        customer=customer,
        amount=amount,
        payment_method=payment_method,
        transaction_reference=transaction_reference or None,
        status=status or Payment.PaymentStatus.PENDING,
    )
    payment.save()
    return payment


def _validate_transition(payment, new_status):
    if new_status not in Payment.PaymentStatus.values:
        raise PaymentError(f"'{new_status}' is not a valid payment status.")
    allowed = VALID_STATUS_TRANSITIONS.get(payment.status, set())
    if new_status == payment.status:
        raise PaymentError(f"Payment is already {payment.status}.")
    if new_status not in allowed:
        raise PaymentError(
            f"Cannot move payment from {payment.status} to {new_status}."
        )


@transaction.atomic
def process_payment_status(payment, new_status):
    _validate_transition(payment, new_status)
    payment.status = new_status
    if new_status == Payment.PaymentStatus.PAID:
        payment.paid_at = timezone.now()
    payment.save()
    return payment


@transaction.atomic
def mark_payment_as_paid(payment, transaction_reference=None):
    if transaction_reference:
        _ensure_unique_reference(transaction_reference, exclude_pk=payment.pk)
        payment.transaction_reference = transaction_reference
    return process_payment_status(payment, Payment.PaymentStatus.PAID)


@transaction.atomic
def refund_payment(payment):
    return process_payment_status(payment, Payment.PaymentStatus.REFUNDED)


def get_payment_details(payment_id):
    try:
        return Payment.objects.select_related("shipment", "customer").get(
            pk=payment_id
        )
    except Payment.DoesNotExist as exc:
        raise PaymentError("Payment not found.") from exc


def get_customer_payment_history(customer):
    return (
        Payment.objects.filter(customer=customer)
        .select_related("shipment")
        .order_by("-created_at")
    )