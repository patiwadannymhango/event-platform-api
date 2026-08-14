from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)

from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, EventMembership
from .serializers import (
    EventDetailSerializer,
    EventListSerializer,
    EventMembershipSerializer,
    EventMembershipWriteSerializer,
    EventWriteSerializer,
)

from apps.common.access import (
    EVENT_ADMIN_ROLES,
    user_has_event_access,
)
from apps.common.permissions import HasEventRole, HasOrganizationRole


class OrganizationEventListView(
    ListAPIView
):
    """
    GET lists events under an org (any member, or superuser). POST
    creates a new event under that org — requires org OWNER/ADMIN.
    """

    serializer_class = (
        EventListSerializer
    )

    def get_permissions(self):
        classes = (
            [IsAuthenticated, HasOrganizationRole("OWNER", "ADMIN")]
            if self.request.method == "POST"
            else [IsAuthenticated]
        )
        return [cls() for cls in classes]

    def get_queryset(self):

        organization_id = self.kwargs[
            "organization_id"
        ]

        if self.request.user.is_superuser:
            return Event.objects.filter(
                organization_id=organization_id,
                is_active=True,
            )

        return Event.objects.filter(
            organization_id=organization_id,
            organization__memberships__user=(
                self.request.user
            ),
            organization__memberships__is_active=True,
            is_active=True,
        ).distinct()

    def post(self, request, organization_id):
        serializer = EventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(organization_id=organization_id)
        return Response(
            EventDetailSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )


class EventDetailView(
    RetrieveAPIView
):
    """
    GET is open to any member with event access (or superuser). PATCH/
    DELETE require event-admin-level access (native EventMembership
    ADMIN, or an org OWNER/ADMIN role bubbling down) — DELETE
    deactivates rather than hard-deleting.
    """

    serializer_class = (
        EventDetailSerializer
    )

    lookup_url_kwarg = "event_id"

    def get_permissions(self):
        classes = (
            [IsAuthenticated]
            if self.request.method == "GET"
            else [IsAuthenticated, HasEventRole(*EVENT_ADMIN_ROLES)]
        )
        return [cls() for cls in classes]

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

    def patch(self, request, event_id):
        event = self.get_object()
        serializer = EventWriteSerializer(
            event, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EventDetailSerializer(event).data)

    def delete(self, request, event_id):
        event = self.get_object()
        event.is_active = False
        event.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventMembershipListCreateView(APIView):
    """
    GET/POST /api/v1/events/<event_id>/members/

    Event-admin-level access only (see EventDetailView docstring).
    """

    def get_permissions(self):
        return [
            IsAuthenticated(),
            HasEventRole(*EVENT_ADMIN_ROLES)(),
        ]

    def get(self, request, event_id):
        memberships = (
            EventMembership.objects
            .filter(event_id=event_id)
            .select_related("user", "event")
        )
        return Response(
            EventMembershipSerializer(memberships, many=True).data
        )

    def post(self, request, event_id):
        serializer = EventMembershipWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership, _ = EventMembership.objects.update_or_create(
            user=serializer.validated_data["user"],
            event_id=event_id,
            defaults={
                "role": serializer.validated_data["role"],
                "is_active": True,
            },
        )

        return Response(
            EventMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class EventMembershipDetailView(APIView):
    """PATCH role / DELETE (=deactivate) a single event membership."""

    def get_permissions(self):
        return [
            IsAuthenticated(),
            HasEventRole(*EVENT_ADMIN_ROLES)(),
        ]

    def patch(self, request, event_id, membership_id):
        membership = get_object_or_404(
            EventMembership,
            id=membership_id,
            event_id=event_id,
        )
        serializer = EventMembershipWriteSerializer(
            membership, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EventMembershipSerializer(membership).data)

    def delete(self, request, event_id, membership_id):
        membership = get_object_or_404(
            EventMembership,
            id=membership_id,
            event_id=event_id,
        )
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)