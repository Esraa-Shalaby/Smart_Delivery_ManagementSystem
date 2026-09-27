from rest_framework.routers import DefaultRouter

from .views import WarehouseViewSet

app_name = "warehouses"

router = DefaultRouter()
router.register(r"warehouses", WarehouseViewSet, basename="warehouse")

urlpatterns = router.urls