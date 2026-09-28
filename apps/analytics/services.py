 
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

DEFAULT_CONFIG = {
    "MANAGER_ROLE": "MANAGER",
    "USER_ROLE_ATTR": "role",
    "SHIPMENT": {
        "model": "shipments.Shipment",
        "status_field": "status",
        "driver_field": "driver",  # FK from Shipment to Driver
        "eta_field": "estimated_delivery",  # set to None if there is no such field
        "pending": ["PENDING"],
        "delivered": ["DELIVERED"],
        "cancelled": ["CANCELLED"],
        "delayed": ["DELAYED"],  # explicit "delayed" status values, if any
    },
    "DRIVER": {
        "model": "drivers.Driver",
        "available_field": "is_available",  # BooleanField
    },
    "PAYMENT": {
        "model": "payments.Payment",
        "status_field": "status",
        "amount_field": "amount",
        "paid": ["PAID"],
        "pending": ["PENDING"],
        "failed": ["FAILED"],
    },
    "COMPLAINT": {
        "model": "complaints.Complaint",
        "status_field": "status",
        "priority_field": "priority",
        "open": ["OPEN", "IN_PROGRESS"],
        "resolved": ["RESOLVED", "CLOSED"],
    },
}

_ZERO = Value(Decimal("0.00"))
_MONEY = DecimalField(max_digits=14, decimal_places=2)


def get_config():
    """Defaults merged with ``settings.ANALYTICS_CONFIG`` (read on every call)."""
    overrides = getattr(settings, "ANALYTICS_CONFIG", None) or {}
    config = {}
    for key, default in DEFAULT_CONFIG.items():
        if isinstance(default, dict):
            config[key] = {**default, **overrides.get(key, {})}
        else:
            config[key] = overrides.get(key, default)
    return config


def _model(section):
    return apps.get_model(get_config()[section]["model"])


def _has_field(model, name):
    try:
        model._meta.get_field(name)
    except FieldDoesNotExist:
        return False
    return True


def _counts_by(queryset, field):
    """{value: count} for ``field`` in a single GROUP BY query."""
    rows = queryset.order_by().values(field).annotate(count=Count("pk"))
    return {(row[field] or "UNKNOWN"): row["count"] for row in rows}


def _sum_for(counts, values):
    return sum(counts.get(value, 0) for value in values)

 
def get_shipment_statistics():
    """Totals per status bucket plus delayed shipments. 2 queries.

    Delayed = an explicit "delayed" status, or a shipment whose estimated
    delivery time has passed while it is neither delivered nor cancelled.
    """
    cfg = get_config()["SHIPMENT"]
    Shipment = _model("SHIPMENT")
    status_field = cfg["status_field"]

    by_status = _counts_by(Shipment.objects.all(), status_field)

    delayed_q = Q(**{f"{status_field}__in": cfg["delayed"]})
    eta_field = cfg["eta_field"]
    if eta_field and _has_field(Shipment, eta_field):
        closed = [*cfg["delivered"], *cfg["cancelled"]]
        delayed_q |= Q(**{f"{eta_field}__lt": timezone.now()}) & ~Q(
            **{f"{status_field}__in": closed}
        )

    return {
        "total_shipments": sum(by_status.values()),
        "pending_shipments": _sum_for(by_status, cfg["pending"]),
        "delivered_shipments": _sum_for(by_status, cfg["delivered"]),
        "cancelled_shipments": _sum_for(by_status, cfg["cancelled"]),
        "delayed_shipments": Shipment.objects.filter(delayed_q).count(),
        "shipments_by_status": by_status,
    }


 
def get_driver_statistics(limit=None):
    """Driver availability and delivery counts per driver. 2 queries.

    ``limit`` keeps only the top N drivers by delivered shipments (used by the
    dashboard); ``None`` returns every driver.
    """
    driver_cfg = get_config()["DRIVER"]
    shipment_cfg = get_config()["SHIPMENT"]
    Driver = _model("DRIVER")
    Shipment = _model("SHIPMENT")

    totals = Driver.objects.aggregate(
        total=Count("pk"),
        available=Count("pk", filter=Q(**{driver_cfg["available_field"]: True})),
    )

    # Reverse lookup name (Driver -> Shipment) taken from the FK itself, so it
    # works with or without a custom related_name.
    rel = Shipment._meta.get_field(shipment_cfg["driver_field"]).related_query_name()
    per_driver = Driver.objects.annotate(
        delivered_count=Count(
            rel, filter=Q(**{f"{rel}__{shipment_cfg['status_field']}__in": shipment_cfg["delivered"]})
        ),
        shipment_count=Count(rel),
    ).order_by("-delivered_count", "pk")
    if limit:
        per_driver = per_driver[:limit]

    return {
        "total_drivers": totals["total"],
        "available_drivers": totals["available"],
        "unavailable_drivers": totals["total"] - totals["available"],
        "deliveries_per_driver": [
            {
                "driver_id": driver.pk,
                "driver": str(driver),
                "delivered_shipments": driver.delivered_count,
                "total_shipments": driver.shipment_count,
            }
            for driver in per_driver
        ],
    }


 
def get_payment_statistics():
    """Payment counts and amounts in a single aggregate query."""
    cfg = get_config()["PAYMENT"]
    Payment = _model("PAYMENT")
    status_field, amount_field = cfg["status_field"], cfg["amount_field"]

    def in_(key):
        return Q(**{f"{status_field}__in": cfg[key]})

    def money(key):
        return Coalesce(
            Sum(amount_field, filter=in_(key)), _ZERO, output_field=_MONEY
        )

    data = Payment.objects.aggregate(
        total_payments=Count("pk"),
        paid_payments=Count("pk", filter=in_("paid")),
        pending_payments=Count("pk", filter=in_("pending")),
        failed_payments=Count("pk", filter=in_("failed")),
        paid_amount=money("paid"),
        pending_amount=money("pending"),
    )
    return data

 
def get_complaint_statistics():
    """Complaint totals and priority breakdown. 2 queries."""
    cfg = get_config()["COMPLAINT"]
    Complaint = _model("COMPLAINT")
    status_field = cfg["status_field"]

    data = Complaint.objects.aggregate(
        total_complaints=Count("pk"),
        open_complaints=Count("pk", filter=Q(**{f"{status_field}__in": cfg["open"]})),
        resolved_complaints=Count(
            "pk", filter=Q(**{f"{status_field}__in": cfg["resolved"]})
        ),
    )
    data["complaints_by_priority"] = _counts_by(
        Complaint.objects.all(), cfg["priority_field"]
    )
    return data


 
def get_dashboard_summary(top_drivers=5):
   
    return {
        "generated_at": timezone.now(),
        "shipments": get_shipment_statistics(),
        "drivers": get_driver_statistics(limit=top_drivers),
        "payments": get_payment_statistics(),
        "complaints": get_complaint_statistics(),
    }