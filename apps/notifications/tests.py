

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications import services
from apps.notifications.models import Notification

User = get_user_model()


def _make_user(username, role, **extra):
    defaults = {"email": f"{username}@example.com", "password": "pass12345"}
    defaults.update(extra)
    user = User.objects.create_user(username=username, **defaults)
    if hasattr(user, "role"):
        user.role = role
        user.save(update_fields=["role"])
    return user


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = _make_user("notif_user1", "CUSTOMER")
        self.other_user = _make_user("notif_user2", "CUSTOMER")

    def test_create_notification_success(self):
        notification = services.create_notification(
            recipient=self.user,
            title="Shipment created",
            message="Your shipment has been created.",
            notification_type=Notification.NotificationType.SHIPMENT_CREATED,
            related_object_id=42,
        )
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        self.assertEqual(notification.related_object_id, 42)

    def test_create_notification_requires_recipient_unless_system(self):
        with self.assertRaises(services.NotificationError):
            services.create_notification(
                title="No recipient",
                message="Should fail",
                notification_type=Notification.NotificationType.PAYMENT_UPDATED,
            )

    def test_create_system_notification_without_recipient(self):
        notification = services.create_notification(
            title="Maintenance window",
            message="The system will be down for maintenance.",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.assertIsNone(notification.recipient)

    def test_create_notification_requires_title_and_message(self):
        with self.assertRaises(services.NotificationError):
            services.create_notification(
                recipient=self.user,
                title="",
                message="msg",
                notification_type=Notification.NotificationType.SYSTEM,
            )
        with self.assertRaises(services.NotificationError):
            services.create_notification(
                recipient=self.user,
                title="title",
                message="",
                notification_type=Notification.NotificationType.SYSTEM,
            )

    def test_create_notification_invalid_type_rejected(self):
        with self.assertRaises(services.NotificationError):
            services.create_notification(
                recipient=self.user,
                title="title",
                message="msg",
                notification_type="NOT_A_REAL_TYPE",
            )

    def test_mark_notification_as_read(self):
        notification = services.create_notification(
            recipient=self.user,
            title="t",
            message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        notification = services.mark_notification_as_read(notification)
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_notification_as_read_is_idempotent(self):
        notification = services.create_notification(
            recipient=self.user,
            title="t",
            message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        notification = services.mark_notification_as_read(notification)
        first_read_at = notification.read_at
        notification = services.mark_notification_as_read(notification)
        self.assertEqual(notification.read_at, first_read_at)

    def test_mark_all_as_read(self):
        for i in range(3):
            services.create_notification(
                recipient=self.user,
                title=f"t{i}",
                message="m",
                notification_type=Notification.NotificationType.SYSTEM,
            )
        services.create_notification(
            recipient=self.other_user,
            title="other",
            message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        marked = services.mark_all_as_read(self.user)
        self.assertEqual(marked, 3)
        self.assertEqual(services.get_unread_notifications(self.user).count(), 0).
        self.assertEqual(services.get_unread_notifications(self.other_user).count(), 1)

    def test_get_unread_notifications(self):
        n1 = services.create_notification(
            recipient=self.user, title="t1", message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        services.create_notification(
            recipient=self.user, title="t2", message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        services.mark_notification_as_read(n1)
        unread = services.get_unread_notifications(self.user)
        self.assertEqual(unread.count(), 1)

    def test_get_user_notifications_only_own(self):
        services.create_notification(
            recipient=self.user, title="mine", message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        services.create_notification(
            recipient=self.other_user, title="not mine", message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        notifications = services.get_user_notifications(self.user)
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().title, "mine")


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = _make_user("notif_api1", "CUSTOMER")
        self.other_user = _make_user("notif_api2", "CUSTOMER")
        self.manager = _make_user("notif_api_mgr", "MANAGER")

        self.own_notification = services.create_notification(
            recipient=self.user,
            title="Your shipment moved",
            message="Status changed to IN_TRANSIT.",
            notification_type=Notification.NotificationType.SHIPMENT_STATUS_CHANGED,
        )
        self.other_notification = services.create_notification(
            recipient=self.other_user,
            title="Not yours",
            message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.system_notification = services.create_notification(
            title="System maintenance",
            message="Downtime tonight.",
            notification_type=Notification.NotificationType.SYSTEM,
        )

    def test_user_lists_only_own_notifications(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data.get("results", response.data)]
        self.assertIn(self.own_notification.id, ids)
        self.assertNotIn(self.other_notification.id, ids)

    def test_user_cannot_retrieve_other_users_notification(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("notification-detail", args=[self.other_notification.id])
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_user_cannot_access_system_notification(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("notification-detail", args=[self.system_notification.id])
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_manager_can_access_system_notification(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get(
            reverse("notification-detail", args=[self.system_notification.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_cannot_access_another_users_personal_notification(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get(
            reverse("notification-detail", args=[self.own_notification.id])
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_unread_endpoint_returns_only_unread(self):
        services.mark_notification_as_read(self.own_notification)
        extra_unread = services.create_notification(
            recipient=self.user, title="new", message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-unread"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data.get("results", response.data)]
        self.assertIn(extra_unread.id, ids)
        self.assertNotIn(self.own_notification.id, ids)

    def test_mark_read_action(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("notification-mark-read", args=[self.own_notification.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own_notification.refresh_from_db()
        self.assertTrue(self.own_notification.is_read)

    def test_mark_read_forbidden_on_other_users_notification(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("notification-mark-read", args=[self.other_notification.id])
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_mark_all_read_action(self):
        services.create_notification(
            recipient=self.user, title="extra", message="m",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("notification-mark-all-read"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["marked_read"], 2)
        self.assertEqual(services.get_unread_notifications(self.user).count(), 0)
        # Other user's notification untouched.
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_anonymous_user_cannot_access(self):
        response = self.client.get(reverse("notification-list"))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )