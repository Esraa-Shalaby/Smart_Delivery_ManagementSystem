 

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.drivers.models import DriverLocation, DriverProfile, Vehicle
from apps.drivers.services import (
    create_or_update_driver_profile,
    get_available_drivers,
    get_driver_assigned_deliveries,
    update_driver_availability,
    update_driver_location,
)
from apps.shipments.services import assign_driver, create_shipment

SHIPMENT_DATA = dict(
    pickup_address="1 Warehouse Rd",
    delivery_address="2 Customer St",
    package_description="Books",
    package_weight=Decimal("2.50"),
    delivery_fee=Decimal("50.00"),
)


def make_user(username, role, **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="strongpass123",
        role=role,
        **extra,
    )


class DriverProfileServiceTests(TestCase):
    """Business logic in drivers/services.py."""

    def setUp(self):
        self.driver = make_user("drv1", User.Role.DRIVER)
        self.customer = make_user("cust1", User.Role.CUSTOMER)

    def test_create_driver_profile_success(self):
        profile = create_or_update_driver_profile(
            user=self.driver, phone="0100000000", license_number="LIC1", vehicle="Small van"
        )
        self.assertEqual(profile.user, self.driver)
        self.assertFalse(profile.is_available)

    def test_create_driver_profile_rejects_non_driver(self):
        with self.assertRaises(ValidationError):
            create_or_update_driver_profile(
                user=self.customer, phone="0100000000", license_number="LIC2"
            )

    def test_update_existing_profile_does_not_duplicate(self):
        create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC3")
        updated = create_or_update_driver_profile(
            user=self.driver, phone="0111111111", license_number="LIC3"
        )
        self.assertEqual(updated.phone, "0111111111")
        self.assertEqual(DriverProfile.objects.filter(user=self.driver).count(), 1)

    def test_update_availability(self):
        profile = create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC4")
        updated = update_driver_availability(driver_profile=profile, is_available=True)
        self.assertTrue(updated.is_available)

    def test_update_location_creates_history(self):
        profile = create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC5")
        update_driver_location(
            driver_profile=profile, latitude=Decimal("30.000000"), longitude=Decimal("31.000000")
        )
        profile.refresh_from_db()
        self.assertEqual(profile.current_latitude, Decimal("30.000000"))
        self.assertEqual(DriverLocation.objects.filter(driver=profile).count(), 1)

    def test_get_available_drivers_filters_correctly(self):
        profile = create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC6")
        self.assertEqual(get_available_drivers().count(), 0)
        update_driver_availability(driver_profile=profile, is_available=True)
        self.assertEqual(get_available_drivers().count(), 1)

    def test_vehicle_linked_to_driver_profile(self):
        profile = create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC7")
        vehicle = Vehicle.objects.create(
            driver=profile, vehicle_type="Van", plate_number="ABC123", capacity=Decimal("500.00")
        )
        self.assertEqual(vehicle.driver, profile)
        self.assertTrue(vehicle.is_active)


class DriverAssignedDeliveriesServiceTests(TestCase):
    """Cross-app read: driver assignments come from apps.shipments."""

    def setUp(self):
        self.driver = make_user("drv2", User.Role.DRIVER)
        self.customer = make_user("cust2", User.Role.CUSTOMER)
        self.manager = make_user("mgr2", User.Role.MANAGER)
        create_or_update_driver_profile(user=self.driver, phone="0100000000", license_number="LIC8")

    def test_assigned_deliveries_reflects_active_assignment(self):
        shipment = create_shipment(customer=self.customer, **SHIPMENT_DATA)
        assign_driver(shipment=shipment, driver=self.driver, assigned_by=self.manager)
        deliveries = get_driver_assigned_deliveries(driver_user=self.driver)
        self.assertEqual(deliveries.count(), 1)


class DriverAPITests(APITestCase):
    """Endpoint behavior, role permissions, and driver data isolation."""

    def setUp(self):
        self.driver = make_user("drvapi", User.Role.DRIVER)
        self.other_driver = make_user("drvapi2", User.Role.DRIVER)
        self.customer = make_user("custapi", User.Role.CUSTOMER)
        self.manager = make_user("mgrapi", User.Role.MANAGER)
        self.profile_url = reverse("drivers:driver-profile")

    def test_driver_can_create_own_profile(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.put(
            self.profile_url, {"phone": "0122222222", "license_number": "LICAPI1", "vehicle": "Van"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone"], "0122222222")

    def test_customer_cannot_access_driver_profile_endpoint(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_can_update_availability(self):
        self.client.force_authenticate(user=self.driver)
        self.client.put(self.profile_url, {"phone": "0100000000", "license_number": "LICAPI2"})
        url = reverse("drivers:driver-availability")
        response = self.client.patch(url, {"is_available": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_available"])

    def test_driver_can_update_location(self):
        self.client.force_authenticate(user=self.driver)
        self.client.put(self.profile_url, {"phone": "0100000000", "license_number": "LICAPI3"})
        url = reverse("drivers:driver-location")
        response = self.client.post(url, {"latitude": "30.111111", "longitude": "31.222222"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_latitude"], "30.111111")

    def test_driver_cannot_view_another_drivers_detail(self):
        self.client.force_authenticate(user=self.driver)
        self.client.put(self.profile_url, {"phone": "0100000000", "license_number": "LICAPI4"})

        self.client.force_authenticate(user=self.other_driver)
        other_response = self.client.put(
            self.profile_url, {"phone": "0133333333", "license_number": "LICAPI5"}
        )
        other_profile_id = other_response.data["id"]

        self.client.force_authenticate(user=self.driver)
        url = reverse("drivers:driver-detail", args=[other_profile_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_view_any_driver_detail(self):
        self.client.force_authenticate(user=self.driver)
        create_response = self.client.put(
            self.profile_url, {"phone": "0100000000", "license_number": "LICAPI6"}
        )
        profile_id = create_response.data["id"]

        self.client.force_authenticate(user=self.manager)
        url = reverse("drivers:driver-detail", args=[profile_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_cannot_view_driver_detail(self):
        self.client.force_authenticate(user=self.driver)
        create_response = self.client.put(
            self.profile_url, {"phone": "0100000000", "license_number": "LICAPI7"}
        )
        profile_id = create_response.data["id"]

        self.client.force_authenticate(user=self.customer)
        url = reverse("drivers:driver-detail", args=[profile_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_manager_can_list_available_drivers(self):
        url = reverse("drivers:available-drivers")

        self.client.force_authenticate(user=self.driver)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.manager)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_access_rejected(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)