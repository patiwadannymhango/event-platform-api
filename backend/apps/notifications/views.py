from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.access import EVENT_VIEW_ROLES
from apps.common.permissions import HasEventRole

from .models import Notification
from .serializers import AdminNotificationSerializer


class AdminEventNotificationListView(ListAPIView):
    """
    GET /api/v1/notifications/admin/events/<event_id>/notifications/

    Read-only delivery log (email/SMS attempts) — there's no template
    model to manage, this just answers "did the runner actually get
    their confirmation".
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]
    serializer_class = AdminNotificationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["channel", "notification_type", "status"]
    search_fields = ["recipient", "subject"]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(registration__event_id=self.kwargs["event_id"])
            .select_related("registration")
        )
