"""
Manager-side views.

The manager sees everything customers create (shipments, customers), assigns drivers,
and drives shipment status changes. Assignments and status changes notify the driver
and the customer so both dashboards reflect them.
"""

from datetime import timedelta
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce, Concat, NullIf, Trim
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.complaints.models import Complaint
from apps.drivers.models import Vehicle
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.shipments.models import DeliveryAssignment, Shipment, ShipmentStatusHistory
from apps.shipments.services import assign_driver, reassign_driver, update_shipment_status

from .roles import RoleOnlyMixin, back_or, display_name, human_duration, notify, role_required

User = get_user_model()
S = Shipment.Status
NType = Notification.NotificationType

# Shipments that are still moving through the pipeline.
NON_TERMINAL = [S.PENDING, S.ASSIGNED, S.PICKED_UP, S.IN_TRANSIT, S.OUT_FOR_DELIVERY]
IN_TRANSIT_GROUP = [S.PICKED_UP, S.IN_TRANSIT, S.OUT_FOR_DELIVERY]

# There is no due-date field on Shipment, so "delayed" = still not finished after this long.
DELAY_AFTER = timedelta(hours=48)
# A driver with this many active deliveries counts as 100% loaded.
MAX_DRIVER_LOAD = 5

FULL_NAME = Coalesce(NullIf(Trim(Concat("first_name", Value(" "), "last_name")), Value("")), "username")


class ManagerOnlyMixin(RoleOnlyMixin):
    role = "MANAGER"


def customers_qs():
    return User.objects.filter(role="CUSTOMER").annotate(full_name=FULL_NAME)


def drivers_qs():
    return User.objects.filter(role="DRIVER").annotate(full_name=FULL_NAME)


def delayed_qs():
    return Shipment.objects.filter(
        status__in=NON_TERMINAL, created_at__lt=timezone.now() - DELAY_AFTER
    )


def with_active_driver(qs):
    """Attach the active assignment (and its driver) to each shipment as `active_assignments`."""
    return qs.select_related("customer").prefetch_related(
        Prefetch(
            "assignments",
            queryset=DeliveryAssignment.objects.filter(is_active=True).select_related(
                "driver", "driver__driver_profile"
            ),
            to_attr="active_assignments",
        )
    )


def shipment_row(shipment, now=None):
    """Flat, template-friendly view of a shipment (needs `with_active_driver`)."""
    now = now or timezone.now()
    assignment = next(iter(getattr(shipment, "active_assignments", [])), None)
    driver = assignment.driver if assignment else None
    profile = getattr(driver, "driver_profile", None) if driver else None
    delayed = shipment.status in NON_TERMINAL and now - shipment.created_at > DELAY_AFTER
    available = bool(profile and profile.is_available)

    return SimpleNamespace(
        pk=shipment.pk,
        tracking_number=shipment.tracking_number,
        customer=display_name(shipment.customer),
        driver=display_name(driver) if driver else "",
        driver_name=display_name(driver) if driver else "",
        driver_availability="available" if available else "offline",
        driver_availability_display="Available" if available else "Offline",
        status=shipment.status.lower(),  # used in CSS classes
        get_status_display=shipment.get_status_display(),
        pickup_address=shipment.pickup_address,
        delivery_address=shipment.delivery_address,
        destination=shipment.delivery_address,
        delivery_fee=shipment.delivery_fee,
        created_at=shipment.created_at,
        is_delayed=delayed,
        delay_duration=human_duration(now - shipment.created_at - DELAY_AFTER) if delayed else "",
        get_absolute_url=f"/manager/shipments/{shipment.pk}/",
        reassign_url=f"/manager/shipments/{shipment.pk}/reassign/",
        manage_url=f"/manager/shipments/{shipment.pk}/",
    )


def driver_rows(users):
    """Flat rows for the drivers table / dashboard overview. `users` must be `drivers_qs()`."""
    users = users.annotate(
        active_deliveries=Count(
            "delivery_assignments", filter=Q(delivery_assignments__is_active=True), distinct=True
        )
    ).select_related("driver_profile").prefetch_related(
        Prefetch(
            "driver_profile__vehicles",
            queryset=Vehicle.objects.filter(is_active=True),
            to_attr="active_vehicles",
        )
    )

    rows = []
    for user in users:
        profile = getattr(user, "driver_profile", None)
        vehicle = next(iter(getattr(profile, "active_vehicles", []) or []), None)
        if user.active_deliveries:
            state = "busy"
        elif profile and profile.is_available:
            state = "available"
        else:
            state = "offline"

        rows.append(SimpleNamespace(
            pk=user.pk,
            id=user.pk,
            name=user.full_name,
            full_name=user.full_name,
            email=user.email,
            phone=profile.phone if profile else "",
            vehicle=(vehicle.vehicle_type if vehicle else (profile.vehicle if profile else "")),
            vehicle_type=vehicle.vehicle_type if vehicle else "",
            vehicle_model=vehicle.model if vehicle else "",
            plate_number=vehicle.plate_number if vehicle else "",
            status=state,
            status_display=state.title(),
            availability=state,
            get_availability_display=state.title(),
            active_deliveries=user.active_deliveries,
            workload_percent=min(100, user.active_deliveries * 100 // MAX_DRIVER_LOAD),
            latitude=profile.current_latitude if profile else None,
            longitude=profile.current_longitude if profile else None,
            is_active=user.is_active,
        ))
    return rows


def _people(qs):
    """(pk, full_name, name) rows for <select> filters."""
    return [
        SimpleNamespace(pk=u.pk, full_name=u.full_name, name=u.full_name)
        for u in qs.order_by("full_name")
    ]


def _date_range(qs, params, field):
    date_from = parse_date(params.get("date_from", ""))
    date_to = parse_date(params.get("date_to", ""))
    if date_from:
        qs = qs.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__date__lte": date_to})
    return qs


# ---------------------------------------------------------------- dashboard
class ManagerDashboardView(ManagerOnlyMixin, TemplateView):
    template_name = "manager/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()

        counts = dict(
            Shipment.objects.order_by().values_list("status").annotate(n=Count("id"))
        )
        total = sum(counts.values())
        ctx["status_counts"] = {s.lower(): counts.get(s, 0) for s in S.values}
        ctx["status_percent"] = {
            s.lower(): round(counts.get(s, 0) * 100 / total) if total else 0 for s in S.values
        }
        ctx["total_shipments"] = total
        ctx["pending_shipments"] = counts.get(S.PENDING, 0)
        ctx["in_transit_shipments"] = sum(counts.get(s, 0) for s in IN_TRANSIT_GROUP)
        ctx["delivered_shipments"] = counts.get(S.DELIVERED, 0)

        delayed = delayed_qs()
        ctx["delayed_count"] = delayed.count()
        ctx["delayed_shipments"] = [
            shipment_row(s, now) for s in with_active_driver(delayed.order_by("created_at"))[:5]
        ]
        ctx["recent_shipments"] = [
            shipment_row(s, now) for s in with_active_driver(Shipment.objects.all())[:8]
        ]

        drivers = driver_rows(drivers_qs())
        ctx["drivers_overview"] = drivers[:6]
        ctx["available_drivers"] = sum(d.status == "available" for d in drivers)
        ctx["busy_drivers"] = sum(d.status == "busy" for d in drivers)
        ctx["offline_drivers"] = sum(d.status == "offline" for d in drivers)
        ctx["active_assignments"] = DeliveryAssignment.objects.filter(is_active=True).count()

        ctx["total_revenue"] = (
            Payment.objects.filter(status=Payment.PaymentStatus.PAID).aggregate(t=Sum("amount"))["t"] or 0
        )

        ctx["recent_complaints"] = [
            SimpleNamespace(
                customer=display_name(c.customer),
                subject=c.subject,
                priority=c.priority.lower(),
                get_priority_display=c.get_priority_display(),
                status=c.status.lower(),
                get_status_display=c.get_status_display(),
                created_at=c.created_at,
            )
            for c in Complaint.objects.select_related("customer").order_by("-created_at")[:5]
        ]
        ctx["recent_activities"] = [
            SimpleNamespace(
                type="shipment",
                message=f"{h.shipment.tracking_number}: "
                        f"{h.get_old_status_display() or 'New'} → {h.get_new_status_display()}",
                description="",
                created_at=h.changed_at,
            )
            for h in ShipmentStatusHistory.objects.select_related("shipment").order_by("-changed_at")[:8]
        ]

        hour = timezone.localtime(now).hour
        ctx["greeting"] = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        return ctx


# ---------------------------------------------------------------- customers
class ManagerCustomersView(ManagerOnlyMixin, TemplateView):
    template_name = "manager/customers.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET

        base = customers_qs()
        ctx["total_customers"] = base.count()
        ctx["active_customers"] = base.filter(is_active=True).count()
        ctx["inactive_customers"] = base.filter(is_active=False).count()
        ctx["customers_with_active_shipments"] = (
            base.filter(shipments__status__in=NON_TERMINAL).distinct().count()
        )
        ctx["new_customers"] = base.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count()
        ctx["new_customers_period"] = "Last 30 days"

        qs = base.annotate(
            total_shipments=Count("shipments", distinct=True),
            delivered_shipments=Count("shipments", filter=Q(shipments__status=S.DELIVERED), distinct=True),
            pending_shipments=Count("shipments", filter=Q(shipments__status=S.PENDING), distinct=True),
            active_shipments=Count("shipments", filter=Q(shipments__status__in=NON_TERMINAL), distinct=True),
            active_complaints=Count(
                "complaints",
                filter=Q(complaints__status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS]),
                distinct=True,
            ),
        ).order_by("-date_joined")

        name = g.get("name", "").strip()
        if name:
            qs = qs.filter(Q(full_name__icontains=name) | Q(username__icontains=name))
        email = g.get("email", "").strip()
        if email:
            qs = qs.filter(email__icontains=email)
        if g.get("status") == "active":
            qs = qs.filter(is_active=True)
        elif g.get("status") == "inactive":
            qs = qs.filter(is_active=False)
        qs = _date_range(qs, g, "date_joined")

        page_obj = Paginator(qs, self.paginate_by).get_page(g.get("page"))
        ctx["page_obj"] = page_obj
        ctx["customers"] = list(page_obj.object_list)
        return ctx


# ---------------------------------------------------------------- shipments
class ManagerShipmentsView(ManagerOnlyMixin, TemplateView):
    template_name = "manager/shipments.html"
    paginate_by = 15

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        now = timezone.now()

        counts = dict(Shipment.objects.order_by().values_list("status").annotate(n=Count("id")))
        ctx["total_shipments"] = sum(counts.values())
        ctx["pending_shipments"] = counts.get(S.PENDING, 0)
        ctx["assigned_shipments"] = counts.get(S.ASSIGNED, 0)
        ctx["in_transit_shipments"] = counts.get(S.PICKED_UP, 0) + counts.get(S.IN_TRANSIT, 0)
        ctx["out_for_delivery_shipments"] = counts.get(S.OUT_FOR_DELIVERY, 0)
        ctx["delivered_shipments"] = counts.get(S.DELIVERED, 0)
        ctx["cancelled_shipments"] = counts.get(S.CANCELLED, 0)
        ctx["delayed_shipments"] = delayed_qs().count()

        qs = Shipment.objects.all()
        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(tracking_number__icontains=q)
                | Q(pickup_address__icontains=q)
                | Q(delivery_address__icontains=q)
                | Q(customer__username__icontains=q)
                | Q(customer__first_name__icontains=q)
                | Q(customer__last_name__icontains=q)
            )
        if g.get("status") in S.values:
            qs = qs.filter(status=g["status"])
        if g.get("customer", "").isdigit():
            qs = qs.filter(customer_id=int(g["customer"]))
        driver = g.get("driver", "")
        if driver == "unassigned":
            qs = qs.exclude(assignments__is_active=True)
        elif driver.isdigit():
            qs = qs.filter(assignments__is_active=True, assignments__driver_id=int(driver))
        qs = _date_range(qs, g, "created_at")

        page_obj = Paginator(with_active_driver(qs.distinct()), self.paginate_by).get_page(g.get("page"))
        ctx["page_obj"] = page_obj
        ctx["shipments"] = [shipment_row(s, now) for s in page_obj.object_list]
        ctx["customers_filter"] = _people(customers_qs())
        ctx["drivers_filter"] = _people(drivers_qs())
        ctx["status_choices"] = S.choices
        return ctx


class ManagerShipmentDetailView(ManagerOnlyMixin, TemplateView):
    template_name = "manager/shipments_details.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        shipment = get_object_or_404(Shipment.objects.select_related("customer"), pk=self.kwargs["pk"])

        assignments = list(shipment.assignments.select_related("driver", "assigned_by"))
        current = next((a for a in assignments if a.is_active), None)

        driver = None
        if current:
            driver = current.driver
            profile = getattr(driver, "driver_profile", None)
            vehicle = profile.vehicles.filter(is_active=True).first() if profile else None
            driver.phone = profile.phone if profile else ""
            driver.vehicle = (vehicle.vehicle_type if vehicle else (profile.vehicle if profile else ""))
            driver.plate_number = vehicle.plate_number if vehicle else ""
            driver.is_available = bool(profile and profile.is_available)

        payment = shipment.payments.order_by("-created_at").first()

        ctx.update(
            shipment=shipment,
            status_history=list(shipment.status_history.select_related("changed_by")),
            assignment_history=assignments,
            driver=driver,
            assignment_date=current.assigned_at if current else None,
            accepted_date=current.accepted_at if current else None,
            complaints=list(shipment.complaints.all()),
            payment=SimpleNamespace(
                amount=payment.amount,
                method=payment.get_payment_method_display(),
                status=payment.get_status_display(),
                transaction_reference=payment.transaction_reference,
                paid_at=payment.paid_at,
            ) if payment else None,
            customer_shipment_count=Shipment.objects.filter(customer=shipment.customer).count(),
        )
        return ctx


def _assign(shipment, driver, manager):
    """Assign a driver, or reassign if the shipment already has one. Notifies both sides."""
    if shipment.assignments.filter(is_active=True).exists():
        reassign_driver(shipment=shipment, new_driver=driver, assigned_by=manager)
    else:
        assign_driver(shipment=shipment, driver=driver, assigned_by=manager)
    shipment.refresh_from_db()

    notify(driver, "New delivery assigned",
           f"Shipment {shipment.tracking_number} was assigned to you.",
           NType.DRIVER_ASSIGNED, shipment.pk)
    notify(shipment.customer, "Driver assigned",
           f"A driver was assigned to shipment {shipment.tracking_number}.",
           NType.DRIVER_ASSIGNED, shipment.pk)


def _change_status(shipment, new_status, manager, note=""):
    update_shipment_status(shipment=shipment, new_status=new_status, changed_by=manager, note=note)
    notify(shipment.customer, "Shipment status updated",
           f"Shipment {shipment.tracking_number} is now {shipment.get_status_display()}.",
           NType.SHIPMENT_STATUS_CHANGED, shipment.pk)


@role_required("MANAGER")
@require_POST
def shipment_assign(request, pk):
    """POST driver_id. Used for both 'assign' and 'reassign'."""
    shipment = get_object_or_404(Shipment, pk=pk)
    driver = drivers_qs().filter(pk=request.POST.get("driver_id") or 0).first()
    if driver is None:
        messages.error(request, "Please choose a valid driver.")
        return back_or(request, f"/manager/shipments/{pk}/")
    try:
        _assign(shipment, driver, request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"{shipment.tracking_number} assigned to {display_name(driver)}.")
    return back_or(request, f"/manager/shipments/{pk}/")


@role_required("MANAGER")
@require_POST
def shipment_update_status(request, pk):
    """POST status (and optional note)."""
    shipment = get_object_or_404(Shipment, pk=pk)
    try:
        _change_status(shipment, request.POST.get("status", ""), request.user,
                       request.POST.get("note", "").strip())
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Status updated to {shipment.get_status_display()}.")
    return back_or(request, f"/manager/shipments/{pk}/")


@role_required("MANAGER")
@require_POST
def shipment_bulk_action(request):
    """POST selected (many), bulk_status and/or bulk_driver - the bar above the shipments table."""
    shipments = Shipment.objects.filter(pk__in=request.POST.getlist("selected"))
    new_status = request.POST.get("bulk_status", "")
    driver = drivers_qs().filter(pk=request.POST.get("bulk_driver") or 0).first()

    if not shipments:
        messages.warning(request, "Select at least one shipment first.")
    elif not new_status and not driver:
        messages.warning(request, "Choose a status or a driver to apply.")
    else:
        ok, failed = 0, []
        for shipment in shipments:
            try:
                if driver:
                    _assign(shipment, driver, request.user)
                if new_status:
                    _change_status(shipment, new_status, request.user, "Bulk update.")
                ok += 1
            except ValidationError as exc:
                failed.append(f"{shipment.tracking_number}: {'; '.join(exc.messages)}")
        if ok:
            messages.success(request, f"{ok} shipment(s) updated.")
        for line in failed:
            messages.error(request, line)
    return back_or(request, "manager:shipments")


# ---------------------------------------------------------------- drivers
class ManagerDriversView(ManagerOnlyMixin, TemplateView):
    template_name = "manager/drivers.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET

        all_rows = driver_rows(drivers_qs())
        ctx["total_drivers"] = len(all_rows)
        ctx["available_drivers"] = sum(d.status == "available" for d in all_rows)
        ctx["busy_drivers"] = sum(d.status == "busy" for d in all_rows)
        ctx["offline_drivers"] = sum(d.status == "offline" for d in all_rows)
        ctx["active_deliveries"] = sum(d.active_deliveries for d in all_rows)
        ctx["available_drivers_list"] = [d for d in all_rows if d.status == "available"][:5]
        ctx["vehicle_types"] = [
            (v, v) for v in Vehicle.objects.order_by("vehicle_type")
            .values_list("vehicle_type", flat=True).distinct()
        ]

        rows = all_rows
        name = g.get("name", "").strip().lower()
        if name:
            rows = [d for d in rows if name in (d.full_name or "").lower()
                    or name in (d.email or "").lower() or name in (d.phone or "").lower()]
        if g.get("vehicle_type"):
            rows = [d for d in rows if d.vehicle_type == g["vehicle_type"]]
        if g.get("status") == "active":
            rows = [d for d in rows if d.is_active]
        elif g.get("status") == "inactive":
            rows = [d for d in rows if not d.is_active]

        page_obj = Paginator(rows, self.paginate_by).get_page(g.get("page"))
        ctx["page_obj"] = page_obj
        ctx["drivers"] = list(page_obj.object_list)
        return ctx


# ---------------------------------------------------------------- activate / deactivate
@role_required("MANAGER")
@require_POST
def user_set_active(request, pk, role, active):
    """Activate/deactivate a customer or driver account (role comes from urls.py)."""
    user = get_object_or_404(User, pk=pk, role=role)
    user.is_active = active
    user.save(update_fields=["is_active"])
    messages.success(request, f"{display_name(user)} {'activated' if active else 'deactivated'}.")
    return back_or(request, "manager:customers" if role == "CUSTOMER" else "manager:drivers")