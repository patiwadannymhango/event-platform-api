from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from .models import Event
from .serializers import (
    EventDetailSerializer,
    EventListSerializer,
)

from apps.common.access import (
    user_has_event_access,
)


class OrganizationEventListView(
    ListAPIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        EventListSerializer
    )

    def get_queryset(self):

        organization_id = self.kwargs[
            "organization_id"
        ]

        return Event.objects.filter(
            organization_id=organization_id,
            organization__memberships__user=(
                self.request.user
            ),
            organization__memberships__is_active=True,
            is_active=True,
        ).distinct()


class EventDetailView(
    RetrieveAPIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        EventDetailSerializer
    )

    lookup_url_kwarg = "event_id"

    def get_object(self):

        event_id = self.kwargs[
            "event_id"
        ]

        if not user_has_event_access(
            self.request.user,
            event_id,
        ):
            from rest_framework.exceptions import (
                PermissionDenied,
            )

            raise PermissionDenied(
                "You do not have access to this event."
            )

        return Event.objects.get(
            id=event_id,
            is_active=True,
        )