from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.access import EVENT_REGISTRATION_MANAGE_ROLES, EVENT_VIEW_ROLES
from apps.common.permissions import HasEventRole

from .models import Notification
from .serializers import AdminNotificationSerializer
from .services import resend_notification_email


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


class AdminNotificationResendView(APIView):
    """
    POST /api/v1/notifications/admin/events/<event_id>/notifications/<id>/resend/
    Body (optional): {"recipient": "someone@example.com"}

    Re-sends a previously logged email — to its original recipient, or to
    a different address the admin types in (the usual reason to resend is
    a bounced or mistyped address). See
    notifications.services.resend_notification_email for how the content
    is rebuilt. Always creates a new Notification row rather than
    mutating the original — the delivery log keeps every attempt.
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_REGISTRATION_MANAGE_ROLES)]

    def post(self, request, event_id, id):
        notification = get_object_or_404(
            Notification.objects.select_related("registration"),
            id=id,
            registration__event_id=event_id,
        )

        if notification.channel != Notification.Channel.EMAIL:
            return Response(
                {"detail": "Only email notifications can be resent."},
                status=400,
            )

        recipient = (request.data.get("recipient") or "").strip() or notification.recipient

        try:
            validate_email(recipient)
        except ValidationError:
            return Response({"detail": "Enter a valid email address."}, status=400)

        new_notification = resend_notification_email(notification, to=recipient)
        data = AdminNotificationSerializer(new_notification).data

        if new_notification.status != Notification.Status.SENT:
            data["detail"] = new_notification.error_message or "Failed to send email."
            return Response(data, status=502)

        return Response(data, status=201)
