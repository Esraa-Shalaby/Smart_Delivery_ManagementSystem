"""
Tests for the accounts app.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from apps.accounts.models import User
from apps.accounts.permissions import IsCustomer, IsDriver, IsManager
from apps.accounts.services import register_user


class UserModelTests(TestCase):
    """User creation, roles, and password hashing at the model level."""

    def test_create_user_with_default_role(self):
        user = User.objects.create_user(
            username="alice", email="alice@example.com", password="strongpass123"
        )
        self.assertEqual(user.role, User.Role.CUSTOMER)

    def test_valid_roles_are_accepted(self):
        for role in (User.Role.CUSTOMER, User.Role.DRIVER, User.Role.MANAGER):
            user = User(username=f"user_{role}", email=f"{role}@example.com", role=role)
            user.set_password("strongpass123")
            user.full_clean()
            user.save()
            self.assertEqual(User.objects.get(username=f"user_{role}").role, role)

    def test_password_is_hashed_not_plain_text(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="strongpass123"
        )
        self.assertNotEqual(user.password, "strongpass123")
        self.assertTrue(user.check_password("strongpass123"))

    def test_email_must_be_unique(self):
        User.objects.create_user(
            username="carol", email="dup@example.com", password="strongpass123"
        )
        duplicate = User(username="carol2", email="dup@example.com", role=User.Role.CUSTOMER)
        duplicate.set_password("strongpass123")
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class UserRegistrationServiceTests(TestCase):
    """Registration service business logic."""

    def test_register_user_hashes_password(self):
        user = register_user(
            username="dave",
            email="dave@example.com",
            password="strongpass123",
            role=User.Role.DRIVER,
        )
        self.assertNotEqual(user.password, "strongpass123")
        self.assertTrue(user.check_password("strongpass123"))
        self.assertEqual(user.role, User.Role.DRIVER)


class UserRegistrationAPITests(APITestCase):
    """Registration endpoint behavior."""

    def setUp(self):
        self.url = reverse("accounts:register")

    def test_register_customer_success(self):
        response = self.client.post(
            self.url,
            {
                "username": "erin",
                "email": "erin@example.com",
                "password": "strongpass123",
                "role": User.Role.CUSTOMER,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(
            username="frank", email="frank@example.com", password="strongpass123"
        )
        response = self.client.post(
            self.url,
            {
                "username": "frank2",
                "email": "frank@example.com",
                "password": "strongpass123",
                "role": User.Role.CUSTOMER,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_manager_without_authorization_forbidden(self):
        response = self.client.post(
            self.url,
            {
                "username": "grace",
                "email": "grace@example.com",
                "password": "strongpass123",
                "role": User.Role.MANAGER,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_manager_by_existing_manager_succeeds(self):
        manager = User.objects.create_user(
            username="boss", email="boss@example.com",
            password="strongpass123", role=User.Role.MANAGER,
        )
        self.client.force_authenticate(user=manager)
        response = self.client.post(
            self.url,
            {
                "username": "newmanager",
                "email": "newmanager@example.com",
                "password": "strongpass123",
                "role": User.Role.MANAGER,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UserProfileAPITests(APITestCase):
    """Authenticated vs. unauthorized access to profile endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="henry", email="henry@example.com", password="strongpass123"
        )
        self.profile_url = reverse("accounts:profile")
        self.update_url = reverse("accounts:profile-update")

    def test_authenticated_user_can_access_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "henry@example.com")

    def test_unauthenticated_user_cannot_access_profile(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_user_cannot_update_profile(self):
        response = self.client.patch(self.update_url, {"first_name": "New"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_update_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.update_url, {"first_name": "Henry"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Henry")


class RolePermissionTests(TestCase):
    """IsCustomer / IsDriver / IsManager permission classes in isolation."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com",
            password="strongpass123", role=User.Role.CUSTOMER,
        )
        self.driver = User.objects.create_user(
            username="drv", email="drv@example.com",
            password="strongpass123", role=User.Role.DRIVER,
        )
        self.manager = User.objects.create_user(
            username="mgr", email="mgr@example.com",
            password="strongpass123", role=User.Role.MANAGER,
        )

    def _request_for(self, user):
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        request.user = user
        return request

    def test_is_customer_allows_only_customer(self):
        permission = IsCustomer()
        self.assertTrue(permission.has_permission(self._request_for(self.customer), None))
        self.assertFalse(permission.has_permission(self._request_for(self.driver), None))
        self.assertFalse(permission.has_permission(self._request_for(self.manager), None))

    def test_is_driver_allows_only_driver(self):
        permission = IsDriver()
        self.assertTrue(permission.has_permission(self._request_for(self.driver), None))
        self.assertFalse(permission.has_permission(self._request_for(self.customer), None))
        self.assertFalse(permission.has_permission(self._request_for(self.manager), None))

    def test_is_manager_allows_only_manager(self):
        permission = IsManager()
        self.assertTrue(permission.has_permission(self._request_for(self.manager), None))
        self.assertFalse(permission.has_permission(self._request_for(self.customer), None))
        self.assertFalse(permission.has_permission(self._request_for(self.driver), None))
