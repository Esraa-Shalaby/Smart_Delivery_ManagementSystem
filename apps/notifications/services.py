

from django.db import transaction
from django.utils import timezone

from .models import Notification


class NotificationError(Exception):
    """Raised for notification validation problems."""


@transaction.atomic
def create_notification(*, title, message, notification_type,
                         recipient=None, related_object_id=None):
    
    if not title or not str(title).strip():
        raise NotificationError("title is required.")
    if not message or not str(message).strip():
        raise NotificationError("message is required.")
    if notification_type not in Notification.NotificationType.values:
        raise NotificationError(f"'{notification_type}' is not a valid notification type.")
    if recipient is None and notification_type != Notification.NotificationType.SYSTEM:
        raise NotificationError(
            "recipient is required for non-SYSTEM notifications."
        )

    notification = Notification(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        related_object_id=related_object_id,
    )
    notification.save()
    return notification


@transaction.atomic
def mark_notification_as_read(notification):
    if notification.is_read:
        return notification
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at"])
    return notification


@transaction.atomic
def mark_all_as_read(user):
    now = timezone.now()
    updated = Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=now
    )
    return updated


def get_unread_notifications(user):
    """Return the queryset of `user`'s unread notifications, newest first."""
    return Notification.objects.filter(recipient=user, is_read=False).order_by(
        "-created_at"
    )


def get_user_notifications(user, *, is_read=None, notification_type=None):
    qs = Notification.objects.filter(recipient=user)
    if is_read is not None:
        qs = qs.filter(is_read=is_read)
    if notification_type:
        qs = qs.filter(notification_type=notification_type)
    return qs.order_by("-created_at")


def get_system_notifications():
    return Notification.objects.filter(recipient__isnull=True).order_by("-created_at")