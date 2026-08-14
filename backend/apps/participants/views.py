from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.common.access import EVENT_VIEW_ROLES
from apps.common.permissions import HasEventRole

from .models import Participant
from .serializers import AdminParticipantSerializer


class AdminEventParticipantListView(ListAPIView):
    """
    GET /api/v1/participants/admin/events/<event_id>/participants/

    Participant isn't org/event-scoped directly (only reachable via
    Registration), so this is the only participant listing exposed — no
    global cross-event/cross-org list, to avoid leaking personal data to
    admins outside the events these people actually registered for.
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]
    serializer_class = AdminParticipantSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "email", "phone"]

    def get_queryset(self):
        return (
            Participant.objects
            .filter(registrations__event_id=self.kwargs["event_id"])
            .distinct()
            .order_by("last_name", "first_name")
        )
