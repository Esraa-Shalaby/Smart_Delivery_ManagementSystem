 
from apps.accounts.models import User

# Which roles may invoke each tool at all.
TOOL_ROLES = {
    "get_delivery_status": {User.Role.CUSTOMER, User.Role.DRIVER, User.Role.MANAGER},
    "get_delayed_deliveries": {User.Role.MANAGER},
    "get_available_drivers": {User.Role.MANAGER},
    "get_driver_details": {User.Role.DRIVER, User.Role.MANAGER},
    "assign_driver": {User.Role.MANAGER},
    "reassign_driver": {User.Role.MANAGER},
    "update_shipment_status": {User.Role.DRIVER, User.Role.MANAGER},
    "get_customer_shipments": {User.Role.CUSTOMER, User.Role.MANAGER},
}


def check_tool_role(*, tool_name, user):
    """
    Raises PermissionError unless the user's role is allowed to use
    this tool at all.
    """
    allowed_roles = TOOL_ROLES.get(tool_name, set())
    if not getattr(user, "is_authenticated", False) or user.role not in allowed_roles:
        raise PermissionError(f"You are not allowed to use the '{tool_name}' tool.")


def check_shipment_access(*, shipment, user):
   
    if user.role == User.Role.MANAGER:
        return
    if user.role == User.Role.CUSTOMER and shipment.customer_id == user.id:
        return
    if user.role == User.Role.DRIVER and shipment.assignments.filter(
        driver=user, is_active=True
    ).exists():
        return
    raise PermissionError("You are not allowed to access this shipment.")


def check_driver_access(*, driver_profile, user):
   
    if user.role == User.Role.MANAGER:
        return
    if user.role == User.Role.DRIVER and driver_profile.user_id == user.id:
        return
    raise PermissionError("You are not allowed to access this driver's information.")