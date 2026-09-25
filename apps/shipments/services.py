"""
Business logic for the shipments app.

Views call these functions; they never perform DB writes directly.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.shipments.models import DeliveryAssignment, Shipment, ShipmentStatusHistory

ALLOWED_TRANSITIONS = {
    Shipment.Status.PENDING: [Shipment.Status.ASSIGNED, Shipment.Status.CANCELLED],
    Shipment.Status.ASSIGNED: [
        Shipment.Status.PICKED_UP,
        Shipment.Status.CANCELLED,
        Shipment.Status.FAILED,
    ],
    Shipment.Status.PICKED_UP: [Shipment.Status.IN_TRANSIT, Shipment.Status.FAILED],
    Shipment.Status.IN_TRANSIT: [Shipment.Status.OUT_FOR_DELIVERY, Shipment.Status.FAILED],
    Shipment.Status.OUT_FOR_DELIVERY: [Shipment.Status.DELIVERED, Shipment.Status.FAILED],
    Shipment.Status.DELIVERED: [],
    Shipment.Status.CANCELLED: [],
    Shipment.Status.FAILED: [],
}


@transaction.atomic
def create_shipment(*, customer, **data):
    """
    Creates a shipment owned by `customer` and records the initial
    status history entry.
    """
    if customer.role != "CUSTOMER":
        raise ValidationError("Only users with the CUSTOMER role can create shipments.")

    shipment = Shipment(customer=customer, **data)
    shipment.full_clean()
    shipment.save()

    ShipmentStatusHistory.objects.create(
        shipment=shipment,
        old_status="",
        new_status=shipment.status,
        changed_by=customer,
        note="Shipment created.",
    )
    return shipment


@transaction.atomic
def assign_driver(*, shipment, driver, assigned_by, note=""):
    """
    Assigns a driver to a shipment that has no active assignment yet.
    Use reassign_driver() to change an already-assigned driver.
    """
    if driver.role != "DRIVER":
        raise ValidationError("Only users with the DRIVER role can be assigned to shipments.")

    if shipment.assignments.filter(is_active=True).exists():
        raise ValidationError(
            "This shipment already has an active driver assignment. Use reassign instead."
        )

    assignment = DeliveryAssignment(shipment=shipment, driver=driver, assigned_by=assigned_by)
    assignment.full_clean()
    assignment.save()

    if shipment.status == Shipment.Status.PENDING:
        update_shipment_status(
            shipment=shipment,
            new_status=Shipment.Status.ASSIGNED,
            changed_by=assigned_by,
            note=note or f"Driver {driver} assigned.",
        )

    return assignment


@transaction.atomic
def reassign_driver(*, shipment, new_driver, assigned_by, note=""):
    """
    Deactivates the shipment's current active assignment (without deleting
    it) and creates a new one for `new_driver`.
    """
    if new_driver.role != "DRIVER":
        raise ValidationError("Only users with the DRIVER role can be assigned to shipments.")

    current_assignment = shipment.assignments.filter(is_active=True).first()
    if current_assignment:
        current_assignment.is_active = False
        current_assignment.save(update_fields=["is_active"])

    new_assignment = DeliveryAssignment(
        shipment=shipment, driver=new_driver, assigned_by=assigned_by
    )
    new_assignment.full_clean()
    new_assignment.save()

    ShipmentStatusHistory.objects.create(
        shipment=shipment,
        old_status=shipment.status,
        new_status=shipment.status,
        changed_by=assigned_by,
        note=note or f"Reassigned to driver {new_driver}.",
    )

    return new_assignment


@transaction.atomic
def update_shipment_status(*, shipment, new_status, changed_by, note=""):
    """
    Transitions a shipment to `new_status`, enforcing the allowed status
    graph and recording the change in ShipmentStatusHistory.
    """
    if new_status not in dict(Shipment.Status.choices):
        raise ValidationError(f"'{new_status}' is not a valid shipment status.")

    allowed_next = ALLOWED_TRANSITIONS.get(shipment.status, [])
    if new_status != shipment.status and new_status not in allowed_next:
        raise ValidationError(
            f"Cannot transition shipment from '{shipment.status}' to '{new_status}'."
        )

    old_status = shipment.status
    shipment.status = new_status
    shipment.full_clean()
    shipment.save(update_fields=["status", "updated_at"])

    ShipmentStatusHistory.objects.create(
        shipment=shipment,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        note=note,
    )

    if new_status in (
        Shipment.Status.DELIVERED,
        Shipment.Status.CANCELLED,
        Shipment.Status.FAILED,
    ):
        active_assignment = shipment.assignments.filter(is_active=True).first()
        if active_assignment:
            active_assignment.completed_at = timezone.now()
            active_assignment.is_active = False
            active_assignment.save(update_fields=["completed_at", "is_active"])

    return shipment


def get_shipment_tracking(*, shipment):
    """
    Returns the shipment's full status history, most recent first.
    """
    return shipment.status_history.all().order_by("-changed_at")