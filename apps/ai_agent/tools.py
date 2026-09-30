 

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.ai_agent.permissions import check_driver_access, check_shipment_access, check_tool_role
from apps.ai_agent.services import log_ai_action
from apps.drivers.models import DriverProfile
from apps.drivers.services import get_available_drivers as list_available_drivers
from apps.drivers.services import get_driver_details as fetch_driver_details
from apps.shipments.models import Shipment
from apps.shipments.services import assign_driver as assign_driver_service
from apps.shipments.services import reassign_driver as reassign_driver_service
from apps.shipments.services import update_shipment_status as update_status_service

DELAY_THRESHOLD_HOURS = 48


def _resolve_shipment(params):
    shipment_id = params.get("shipment_id")
    tracking_number = params.get("tracking_number")

    if shipment_id:
        return Shipment.objects.get(pk=shipment_id)
    if tracking_number:
        return Shipment.objects.get(tracking_number=tracking_number)
    raise ValueError("A shipment_id or tracking_number is required.")


def _get_delivery_status(*, params, user):
    shipment = _resolve_shipment(params)
    check_shipment_access(shipment=shipment, user=user)
    return {
        "tracking_number": shipment.tracking_number,
        "status": shipment.status,
        "pickup_address": shipment.pickup_address,
        "delivery_address": shipment.delivery_address,
        "updated_at": shipment.updated_at.isoformat(),
    }


def _get_delayed_deliveries(*, params, user):
    cutoff = timezone.now() - timedelta(hours=DELAY_THRESHOLD_HOURS)
    active_statuses = [
        Shipment.Status.PENDING,
        Shipment.Status.ASSIGNED,
        Shipment.Status.PICKED_UP,
        Shipment.Status.IN_TRANSIT,
        Shipment.Status.OUT_FOR_DELIVERY,
    ]
    delayed = Shipment.objects.filter(status__in=active_statuses, created_at__lte=cutoff)
    return {
        "count": delayed.count(),
        "shipments": [
            {
                "tracking_number": s.tracking_number,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in delayed[:20]
        ],
    }


def _get_available_drivers(*, params, user):
    drivers = list_available_drivers()
    return {
        "count": drivers.count(),
        "drivers": [
            {
                "driver_profile_id": d.id,
                "username": d.user.username,
                "phone": d.phone,
                "vehicle": d.vehicle,
            }
            for d in drivers[:20]
        ],
    }


def _get_driver_details(*, params, user):
    driver_profile_id = params.get("driver_profile_id")

    if not driver_profile_id and user.role == User.Role.DRIVER:
        profile = DriverProfile.objects.filter(user=user).first()
        if not profile:
            raise ValueError("No driver profile found for this account.")
        driver_profile_id = profile.id

    if not driver_profile_id:
        raise ValueError("A driver_profile_id is required.")

    profile = fetch_driver_details(driver_profile_id=driver_profile_id)
    check_driver_access(driver_profile=profile, user=user)

    return {
        "driver_profile_id": profile.id,
        "username": profile.user.username,
        "phone": profile.phone,
        "license_number": profile.license_number,
        "vehicle": profile.vehicle,
        "is_available": profile.is_available,
    }


def _assign_driver(*, params, user):
    shipment = _resolve_shipment(params)
    driver_id = params.get("driver_id")
    if not driver_id:
        raise ValueError("A driver_id is required.")

    driver = User.objects.get(pk=driver_id, role=User.Role.DRIVER)
    assignment = assign_driver_service(
        shipment=shipment, driver=driver, assigned_by=user, note="Assigned via AI agent."
    )
    return {
        "shipment_tracking_number": shipment.tracking_number,
        "driver": driver.username,
        "assignment_id": assignment.id,
        "is_active": assignment.is_active,
    }


def _reassign_driver(*, params, user):
    shipment = _resolve_shipment(params)
    driver_id = params.get("driver_id")
    if not driver_id:
        raise ValueError("A driver_id is required.")

    new_driver = User.objects.get(pk=driver_id, role=User.Role.DRIVER)
    assignment = reassign_driver_service(
        shipment=shipment, new_driver=new_driver, assigned_by=user, note="Reassigned via AI agent."
    )
    return {
        "shipment_tracking_number": shipment.tracking_number,
        "driver": new_driver.username,
        "assignment_id": assignment.id,
        "is_active": assignment.is_active,
    }


def _update_shipment_status(*, params, user):
    shipment = _resolve_shipment(params)
    check_shipment_access(shipment=shipment, user=user)

    new_status = params.get("status")
    if not new_status:
        raise ValueError("A status value is required.")

    updated = update_status_service(
        shipment=shipment, new_status=new_status, changed_by=user, note="Updated via AI agent."
    )
    return {"tracking_number": updated.tracking_number, "status": updated.status}


def _get_customer_shipments(*, params, user):
    if user.role == User.Role.MANAGER:
        customer_id = params.get("customer_id")
        if not customer_id:
            raise ValueError("A customer_id is required for managers.")
        queryset = Shipment.objects.filter(customer_id=customer_id)
    else:
        queryset = Shipment.objects.filter(customer=user)

    shipments = list(queryset[:20])
    return {
        "count": len(shipments),
        "shipments": [
            {
                "tracking_number": s.tracking_number,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in shipments
        ],
    }


def _get_my_deliveries(*, params, user):
    shipments = list(
        Shipment.objects.filter(
            assignments__driver=user, assignments__is_active=True
        ).distinct()[:20]
    )
    return {
        "count": len(shipments),
        "shipments": [
            {
                "tracking_number": s.tracking_number,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in shipments
        ],
    }


TOOL_REGISTRY = {
    "get_delivery_status": _get_delivery_status,
    "get_delayed_deliveries": _get_delayed_deliveries,
    "get_available_drivers": _get_available_drivers,
    "get_driver_details": _get_driver_details,
    "assign_driver": _assign_driver,
    "reassign_driver": _reassign_driver,
    "update_shipment_status": _update_shipment_status,
    "get_customer_shipments": _get_customer_shipments,
    "get_my_deliveries": _get_my_deliveries,
}


def _format_reply(tool_name, data):
    if tool_name == "get_delivery_status":
        return f"Shipment {data['tracking_number']} is currently {data['status']}."
    if tool_name == "get_delayed_deliveries":
        return f"There are {data['count']} delayed shipment(s)."
    if tool_name == "get_available_drivers":
        return f"There are {data['count']} available driver(s) right now."
    if tool_name == "get_driver_details":
        return f"Driver {data['username']} — available: {data['is_available']}."
    if tool_name == "assign_driver":
        return f"Driver {data['driver']} was assigned to shipment {data['shipment_tracking_number']}."
    if tool_name == "reassign_driver":
        return f"Shipment {data['shipment_tracking_number']} was reassigned to driver {data['driver']}."
    if tool_name == "update_shipment_status":
        return f"Shipment {data['tracking_number']} status updated to {data['status']}."
    if tool_name == "get_customer_shipments":
        return f"You have {data['count']} shipment(s)."
    if tool_name == "get_my_deliveries":
        return f"You have {data['count']} active delivery(ies)."
    return "Done."


def execute_tool(*, tool_name, params, user, raw_message=""):
    """
    Runs the full authorization -> validation -> service -> audit-log
    pipeline for a single tool call and returns a JSON-safe result.
    Never lets a caller bypass authorization, and always logs the
    attempt (successful or not).
    """
    params = params or {}
    handler = TOOL_REGISTRY.get(tool_name)

    if handler is None:
        log_ai_action(
            user=user, action=tool_name, input_data=params,
            result={"error": "Unknown tool."}, success=False,
        )
        return {"success": False, "reply": "Sorry, I couldn't understand that request.", "tool": tool_name}

    try:
        check_tool_role(tool_name=tool_name, user=user)
        data = handler(params=params, user=user)
    except PermissionError as exc:
        log_ai_action(
            user=user, action=tool_name, input_data=params,
            result={"error": str(exc)}, success=False,
        )
        return {"success": False, "reply": str(exc), "tool": tool_name}
    except (ValueError, DjangoValidationError) as exc:
        message = exc.messages[0] if isinstance(exc, DjangoValidationError) else str(exc)
        log_ai_action(
            user=user, action=tool_name, input_data=params,
            result={"error": message}, success=False,
        )
        return {"success": False, "reply": message, "tool": tool_name}
    except ObjectDoesNotExist:
        log_ai_action(
            user=user, action=tool_name, input_data=params,
            result={"error": "Not found."}, success=False,
        )
        return {"success": False, "reply": "I couldn't find that record.", "tool": tool_name}

    log_ai_action(user=user, action=tool_name, input_data=params, result=data, success=True)
    return {"success": True, "reply": _format_reply(tool_name, data), "tool": tool_name, "data": data}