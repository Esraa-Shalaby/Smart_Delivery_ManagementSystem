
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.warehouses import services
from apps.warehouses.models import Warehouse

User = get_user_model()


def _make_user(username, role, **extra):
    defaults = {"email": f"{username}@example.com", "password": "pass12345"}
    defaults.update(extra)
    user = User.objects.create_user(username=username, **defaults)
    if hasattr(user, "role"):
        user.role = role
        user.save(update_fields=["role"])
    return user


class WarehouseModelAndServiceTests(TestCase):
    def test_create_warehouse_success(self):
        warehouse = services.create_warehouse(
            name="Main Hub",
            code="wh-cai-01",
            address="123 Industrial Rd",
            city="Cairo",
            phone="0100000000",
            latitude="30.044420",
            longitude="31.235712",
        )
        self.assertTrue(warehouse.is_active)
        # code should be normalized to uppercase.
        self.assertEqual(warehouse.code, "WH-CAI-01")

    def test_duplicate_code_rejected(self):
        services.create_warehouse(name="Hub A", code="WH-1", address="Addr", city="Cairo")
        with self.assertRaises(services.WarehouseError):
            services.create_warehouse(name="Hub B", code="wh-1", address="Addr", city="Giza")

    def test_missing_required_fields_rejected(self):
        with self.assertRaises(services.WarehouseError):
            services.create_warehouse(name="", code="WH-2", address="Addr", city="Cairo")
        with self.assertRaises(services.WarehouseError):
            services.create_warehouse(name="Hub", code="", address="Addr", city="Cairo")

    def test_update_warehouse(self):
        warehouse = services.create_warehouse(
            name="Hub A", code="WH-3", address="Addr", city="Cairo"
        )
        updated = services.update_warehouse(warehouse, name="Hub A Renamed", city="Alexandria")
        self.assertEqual(updated.name, "Hub A Renamed")
        self.assertEqual(updated.city, "Alexandria")

    def test_update_warehouse_duplicate_code_rejected(self):
        services.create_warehouse(name="Hub A", code="WH-4", address="Addr", city="Cairo")
        warehouse_b = services.create_warehouse(
            name="Hub B", code="WH-5", address="Addr", city="Giza"
        )
        with self.assertRaises(services.WarehouseError):
            services.update_warehouse(warehouse_b, code="WH-4")

    def test_activate_deactivate_warehouse(self):
        warehouse = services.create_warehouse(
            name="Hub A", code="WH-6", address="Addr", city="Cairo"
        )
        self.assertTrue(warehouse.is_active)

        warehouse = services.deactivate_warehouse(warehouse)
        self.assertFalse(warehouse.is_active)

        with self.assertRaises(services.WarehouseError):
            services.deactivate_warehouse(warehouse)

        warehouse = services.activate_warehouse(warehouse)
        self.assertTrue(warehouse.is_active)

        with self.assertRaises(services.WarehouseError):
            services.activate_warehouse(warehouse)

    def test_list_warehouses_filters(self):
        services.create_warehouse(name="Cairo Hub", code="WH-7", address="A", city="Cairo")
        inactive = services.create_warehouse(
            name="Giza Hub", code="WH-8", address="A", city="Giza"
        )
        services.deactivate_warehouse(inactive)

        self.assertEqual(services.list_warehouses().count(), 2)
        self.assertEqual(services.list_warehouses(is_active=True).count(), 1)
        self.assertEqual(services.list_warehouses(is_active=False).count(), 1)
        self.assertEqual(services.list_warehouses(city="Cairo").count(), 1)
        self.assertEqual(services.list_warehouses(search="Giza").count(), 1)

    def test_get_warehouse_details_not_found(self):
        with self.assertRaises(services.WarehouseError):
            services.get_warehouse_details(999999)


class WarehouseAPITests(APITestCase):
    def setUp(self):
        self.customer = _make_user("wh_cust1", "CUSTOMER")
        self.driver = _make_user("wh_drv1", "DRIVER")
        self.manager = _make_user("wh_mgr1", "MANAGER")

        self.warehouse = services.create_warehouse(
            name="Main Hub", code="WH-API-1", address="Addr", city="Cairo"
        )

    def test_anonymous_user_cannot_access(self):
        response = self.client.get(reverse("warehouse-list"))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_customer_can_list_warehouses(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("warehouse-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_driver_can_view_warehouse_detail(self):
        self.client.force_authenticate(self.driver)
        response = self.client.get(reverse("warehouse-detail", args=[self.warehouse.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_cannot_create_warehouse(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("warehouse-list"),
            {"name": "New Hub", "code": "WH-API-2", "address": "Addr", "city": "Cairo"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_update_warehouse(self):
        self.client.force_authenticate(self.driver)
        response = self.client.patch(
            reverse("warehouse-detail", args=[self.warehouse.id]), {"city": "Giza"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_warehouse(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            reverse("warehouse-list"),
            {"name": "New Hub", "code": "WH-API-3", "address": "Addr", "city": "Cairo"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["code"], "WH-API-3")

    def test_manager_create_duplicate_code_rejected(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            reverse("warehouse-list"),
            {"name": "Dup Hub", "code": "wh-api-1", "address": "Addr", "city": "Cairo"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_can_update_warehouse(self):
        self.client.force_authenticate(self.manager)
        response = self.client.patch(
            reverse("warehouse-detail", args=[self.warehouse.id]), {"city": "Alexandria"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["city"], "Alexandria")

    def test_manager_can_deactivate_and_activate(self):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            reverse("warehouse-deactivate", args=[self.warehouse.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.warehouse.refresh_from_db()
        self.assertFalse(self.warehouse.is_active)

        response = self.client.post(
            reverse("warehouse-activate", args=[self.warehouse.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.warehouse.refresh_from_db()
        self.assertTrue(self.warehouse.is_active)

    def test_customer_cannot_deactivate_warehouse(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("warehouse-deactivate", args=[self.warehouse.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_delete_warehouse(self):
        self.client.force_authenticate(self.manager)
        response = self.client.delete(
            reverse("warehouse-detail", args=[self.warehouse.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Warehouse.objects.filter(pk=self.warehouse.id).exists())

    def test_customer_cannot_delete_warehouse(self):
        self.client.force_authenticate(self.customer)
        response = self.client.delete(
            reverse("warehouse-detail", args=[self.warehouse.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_warehouse_hidden_from_non_manager_by_default(self):
        services.deactivate_warehouse(self.warehouse)
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("warehouse-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data.get("results", response.data)]
        self.assertNotIn(self.warehouse.id, ids)

    def test_manager_sees_inactive_warehouses_by_default(self):
        services.deactivate_warehouse(self.warehouse)
        self.client.force_authenticate(self.manager)
        response = self.client.get(reverse("warehouse-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data.get("results", response.data)]
        self.assertIn(self.warehouse.id, ids)