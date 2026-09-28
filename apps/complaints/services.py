 
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.complaints.models import Complaint

ALLOWED_TRANSITIONS = {
    Complaint.Status.OPEN: [Complaint.Status.IN_PROGRESS, Complaint.Status.CLOSED],
    Complaint.Status.IN_PROGRESS: [Complaint.Status.RESOLVED, Complaint.Status.CLOSED],
    Complaint.Status.RESOLVED: [Complaint.Status.CLOSED],
    Complaint.Status.CLOSED: [],
}


@transaction.atomic
def create_complaint(*, customer, **data):
     
    if customer.role != "CUSTOMER":
        raise ValidationError("Only users with the CUSTOMER role can file complaints.")

    complaint = Complaint(customer=customer, **data)
    complaint.full_clean()
    complaint.save()
    return complaint


@transaction.atomic
def update_complaint_status(*, complaint, new_status, changed_by):
   
    if new_status not in dict(Complaint.Status.choices):
        raise ValidationError(f"'{new_status}' is not a valid complaint status.")

    allowed_next = ALLOWED_TRANSITIONS.get(complaint.status, [])
    if new_status != complaint.status and new_status not in allowed_next:
        raise ValidationError(
            f"Cannot transition complaint from '{complaint.status}' to '{new_status}'."
        )

    complaint.status = new_status
    if new_status == Complaint.Status.RESOLVED and not complaint.resolved_at:
        complaint.resolved_at = timezone.now()
        complaint.resolved_by = changed_by

    complaint.full_clean()
    complaint.save()
    return complaint


@transaction.atomic
def respond_to_complaint(*, complaint, response, responded_by):
     
    complaint.response = response

    if complaint.status == Complaint.Status.OPEN:
        complaint.status = Complaint.Status.IN_PROGRESS

    complaint.full_clean()
    complaint.save()
    return complaint


@transaction.atomic
def resolve_complaint(*, complaint, resolved_by, response=""):
    """
    Marks a complaint RESOLVED, optionally updating the response text.
    """
    allowed_next = ALLOWED_TRANSITIONS.get(complaint.status, [])
    if (
        complaint.status != Complaint.Status.RESOLVED
        and Complaint.Status.RESOLVED not in allowed_next
    ):
        raise ValidationError(
            f"Cannot resolve a complaint that is currently '{complaint.status}'."
        )

    if response:
        complaint.response = response

    complaint.status = Complaint.Status.RESOLVED
    complaint.resolved_by = resolved_by
    complaint.resolved_at = timezone.now()

    complaint.full_clean()
    complaint.save()
    return complaint


def list_customer_complaints(*, customer):
     
    return Complaint.objects.filter(customer=customer)


def list_all_complaints():
     
    return Complaint.objects.all()