from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Notification
from .permissions import NotificationAccessPermission, _is_manager
from .serializers import MarkAllReadResponseSerializer, NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
   
    serializer_class = NotificationSerializer
    permission_classes = [NotificationAccessPermission]

    def get_queryset(self):
        user = self.request.user
        own = Notification.objects.filter(recipient=user)
        if _is_manager(user):
            own = own | services.get_system_notifications()
        return own.order_by("-created_at")

    @action(detail=False, methods=["get"], url_path="unread")
    def unread(self, request):
        notifications = services.get_unread_notifications(request.user)
        page = self.paginate_queryset(notifications)
        serializer = self.get_serializer(page if page is not None else notifications, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification = services.mark_notification_as_read(notification)
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        marked_read = services.mark_all_as_read(request.user)
        serializer = MarkAllReadResponseSerializer({"marked_read": marked_read})
        return Response(serializer.data)