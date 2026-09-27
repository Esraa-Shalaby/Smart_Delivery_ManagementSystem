

from django.db import transaction

from .models import Warehouse


class WarehouseError(Exception):


def _ensure_unique_code(code, *, exclude_pk=None):
    if not code:
        return
    normalized = code.strip().upper()
    qs = Warehouse.objects.filter(code__iexact=normalized)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise WarehouseError("code must be unique.")


@transaction.atomic
def create_warehouse(*, name, code, address, city, phone="", latitude=None,
                      longitude=None, is_active=True):
    """Create a new warehouse. Raises WarehouseError if `code` is taken."""
    if not name or not str(name).strip():
        raise WarehouseError("name is required.")
    if not code or not str(code).strip():
        raise WarehouseError("code is required.")

    _ensure_unique_code(code)

    warehouse = Warehouse(
        name=name,
        code=code,
        address=address,
        city=city,
        phone=phone or "",
        latitude=latitude,
        longitude=longitude,
        is_active=is_active,
    )
    warehouse.save()
    return warehouse


@transaction.atomic
def update_warehouse(warehouse, **fields):
    allowed_fields = {
        "name", "code", "address", "city", "phone",
        "latitude", "longitude", "is_active",
    }
    updates = {k: v for k, v in fields.items() if k in allowed_fields}

    new_code = updates.get("code")
    if new_code:
        _ensure_unique_code(new_code, exclude_pk=warehouse.pk)

    for field, value in updates.items():
        setattr(warehouse, field, value)

    warehouse.save()
    return warehouse


@transaction.atomic
def activate_warehouse(warehouse):
    """Mark a warehouse as active."""
    if warehouse.is_active:
        raise WarehouseError("Warehouse is already active.")
    warehouse.is_active = True
    warehouse.save(update_fields=["is_active", "updated_at"])
    return warehouse


@transaction.atomic
def deactivate_warehouse(warehouse):
    if not warehouse.is_active:
        raise WarehouseError("Warehouse is already inactive.")
    warehouse.is_active = False
    warehouse.save(update_fields=["is_active", "updated_at"])
    return warehouse


def list_warehouses(*, is_active=None, city=None, search=None):
    qs = Warehouse.objects.all()
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if city:
        qs = qs.filter(city__iexact=city)
    if search:
        from django.db.models import Q

        qs = qs.filter(
            Q(name__icontains=search)
            | Q(code__icontains=search)
            | Q(city__icontains=search)
        )
    return qs.order_by("name")


def get_warehouse_details(warehouse_id):
    try:
        return Warehouse.objects.get(pk=warehouse_id)
    except Warehouse.DoesNotExist as exc:
        raise WarehouseError("Warehouse not found.") from exc