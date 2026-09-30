"""
Driver-side views.

A driver sees the shipments the manager assigned to them (DeliveryAssignment),
can accept an assignment and move the shipment through its status flow.
Every status change notifies the customer, so the customer dashboard stays in sync.
"""

from types import SimpleNamespace

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.notifications.models import Notification
from apps.shipments.models import DeliveryAssignment, Shipment
from apps.shipments.services import ALLOWED_TRANSITIONS, update_shipment_status

from .roles import RoleOnlyMixin, human_duration, notify, role_required

S = Shipment.Status
NType = Notification.NotificationType

# Statuses where the driver is already on the road.
IN_MOTION = [S.PICKED_UP, S.IN_TRANSIT, S.OUT_FOR_DELIVERY]

# Button labels for the transitions a driver is allowed to trigger (drivers can't cancel).
DRIVER_ACTIONS = {
    S.PICKED_UP: "Mark as Picked Up",
    S.IN_TRANSIT: "Start Transit",
    S.OUT_FOR_DELIVERY: "Out for Delivery",
    S.DELIVERED: "Mark as Delivered",
    S.FAILED: "Report Failed Delivery",
}


def my_assignments(user):
    return DeliveryAssignment.objects.filter(driver=user).select_related(
        "shipment", "shipment__customer"
    )


def apply_filters(qs, params):
    q = params.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(shipment__tracking_number__icontains=q)
            | Q(shipment__pickup_address__icontains=q)
            | Q(shipment__delivery_address__icontains=q)
        )
    status = params.get("status")
    if status in Shipment.Status.values:
        qs = qs.filter(shipment__status=status)
    date_from = parse_date(params.get("date_from", ""))
    date_to = parse_date(params.get("date_to", ""))
    if date_from:
        qs = qs.filter(assigned_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(assigned_at__date__lte=date_to)
    return qs


def allowed_transitions(delivery):
    """Status buttons for the detail page. The driver must accept the assignment first."""
    if not delivery.is_active or delivery.accepted_at is None:
        return []
    return [
        SimpleNamespace(value=str(s.value), label=DRIVER_ACTIONS[s])
        for s in ALLOWED_TRANSITIONS.get(delivery.shipment.status, [])
        if s in DRIVER_ACTIONS
    ]


class DriverOnlyMixin(RoleOnlyMixin):
    role = "DRIVER"


class DriverDashboardView(DriverOnlyMixin, TemplateView):
    template_name = "driver/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        mine = my_assignments(user)
        active = mine.filter(is_active=True)
        history = mine.filter(is_active=False)

        profile = getattr(user, "driver_profile", None)
        vehicle = profile.vehicles.filter(is_active=True).first() if profile else None
        ctx["driver"] = SimpleNamespace(
            is_available=bool(profile and profile.is_available),
            vehicle=(profile.vehicle if profile and profile.vehicle else
                     (f"{vehicle.vehicle_type} {vehicle.model}".strip() if vehicle else "")),
            plate_number=vehicle.plate_number if vehicle else "",
            availability_updated_at=profile.updated_at if profile else None,
        )

        ctx["assigned_count"] = active.count()
        ctx["active_count"] = active.filter(shipment__status__in=IN_MOTION).count()
        ctx["completed_count"] = history.filter(shipment__status=S.DELIVERED).count()
        ctx["pending_count"] = active.filter(accepted_at__isnull=True).count()

        ctx["active_delivery"] = (
            active.filter(shipment__status__in=IN_MOTION).first() or active.first()
        )
        ctx["today_deliveries"] = list(active[:5])
        ctx["recent_history"] = list(history[:5])

        notifications = Notification.objects.filter(recipient=user)
        ctx["unread_notifications_count"] = notifications.filter(is_read=False).count()
        ctx["recent_notifications"] = list(notifications[:5])
        return ctx


class DriverDeliveriesView(DriverOnlyMixin, TemplateView):
    template_name = "driver/deliveries.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mine = my_assignments(self.request.user)
        active = mine.filter(is_active=True)

        ctx["total_assigned"] = active.count()
        ctx["active_count"] = active.filter(shipment__status__in=IN_MOTION).count()
        ctx["completed_count"] = mine.filter(shipment__status=S.DELIVERED).count()
        ctx["pending_count"] = active.filter(accepted_at__isnull=True).count()

        qs = apply_filters(active, self.request.GET)
        page_obj = Paginator(qs, self.paginate_by).get_page(self.request.GET.get("page"))
        ctx["page_obj"] = page_obj
        ctx["deliveries"] = list(page_obj.object_list)
        return ctx


class DriverHistoryView(DriverOnlyMixin, TemplateView):
    template_name = "driver/history.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        done = my_assignments(self.request.user).filter(is_active=False)

        ctx["completed_count"] = done.filter(shipment__status=S.DELIVERED).count()
        ctx["failed_count"] = done.filter(shipment__status=S.FAILED).count()
        ctx["total_count"] = done.count()

        qs = apply_filters(done, self.request.GET)
        page_obj = Paginator(qs, self.paginate_by).get_page(self.request.GET.get("page"))
        entries = list(page_obj.object_list)
        for entry in entries:
            entry.duration = (
                human_duration(entry.completed_at - entry.assigned_at)
                if entry.completed_at else ""
            )
        ctx["page_obj"] = page_obj
        ctx["history"] = entries
        return ctx


class DriverDeliveryDetailView(DriverOnlyMixin, TemplateView):
    template_name = "driver/delivery_deatails.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        delivery = get_object_or_404(my_assignments(self.request.user), pk=self.kwargs["pk"])
        delivery.can_accept = delivery.is_active and delivery.accepted_at is None

        labels = dict(Shipment.Status.choices)
        history = list(delivery.shipment.status_history.select_related("changed_by"))
        for event in history:
            event.old_status_display = labels.get(event.old_status, "")
            event.new_status_display = labels.get(event.new_status, event.new_status)

        ctx["delivery"] = delivery
        ctx["status_history"] = history
        ctx["allowed_transitions"] = allowed_transitions(delivery)
        return ctx


@role_required("DRIVER")
@require_POST
def accept_delivery(request, pk):
    delivery = get_object_or_404(my_assignments(request.user), pk=pk, is_active=True)
    if delivery.accepted_at:
        messages.info(request, "You already accepted this delivery.")
    else:
        delivery.accepted_at = timezone.now()
        delivery.save(update_fields=["accepted_at"])
        shipment = delivery.shipment
        notify(
            shipment.customer,
            "Driver accepted your shipment",
            f"Your driver accepted shipment {shipment.tracking_number}.",
            NType.SHIPMENT_STATUS_CHANGED,
            shipment.pk,
        )
        messages.success(request, "Delivery accepted.")
    return redirect("driver:delivery_detail", pk=pk)


@role_required("DRIVER")
@require_POST
def update_delivery_status(request, pk):
    delivery = get_object_or_404(my_assignments(request.user), pk=pk)
    new_status = request.POST.get("status", "")

    if new_status not in {t.value for t in allowed_transitions(delivery)}:
        messages.error(request, "That status change isn't allowed right now.")
        return redirect("driver:delivery_detail", pk=pk)

    shipment = delivery.shipment
    try:
        update_shipment_status(
            shipment=shipment,
            new_status=new_status,
            changed_by=request.user,
            note=request.POST.get("note", "").strip(),
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("driver:delivery_detail", pk=pk)

    notify(
        shipment.customer,
        "Shipment status updated",
        f"Shipment {shipment.tracking_number} is now {shipment.get_status_display()}.",
        NType.SHIPMENT_STATUS_CHANGED,
        shipment.pk,
    )
    messages.success(request, f"Status updated to {shipment.get_status_display()}.")
    return redirect("driver:delivery_detail", pk=pk)