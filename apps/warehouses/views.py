from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Warehouse
from .permissions import WarehouseAccessPermission, _is_manager
from .serializers import (
    WarehousePublicSerializer,
    WarehouseSerializer,
    WarehouseStatusActionSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
  

    permission_classes = [WarehouseAccessPermission]
    queryset = Warehouse.objects.all()

    def get_queryset(self):
        params = self.request.query_params
        is_active_param = params.get("is_active")
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("1", "true", "yes")

        # Non-manager roles only ever see active warehouses by default,
        # unless "is_active" was explicitly requested (still read-only).
        if is_active is None and not _is_manager(self.request.user):
            is_active = True

        return services.list_warehouses(
            is_active=is_active,
            city=params.get("city"),
            search=params.get("search"),
        )

    def get_serializer_class(self):
        if _is_manager(self.request.user):
            return WarehouseSerializer
        return WarehousePublicSerializer

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        warehouse = self.get_object()
        serializer = WarehouseStatusActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            warehouse = services.activate_warehouse(warehouse)
        except services.WarehouseError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        return Response(WarehouseSerializer(warehouse).data)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        warehouse = self.get_object()
        serializer = WarehouseStatusActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            warehouse = services.deactivate_warehouse(warehouse)
        except services.WarehouseError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        return Response(WarehouseSerializer(warehouse).data)