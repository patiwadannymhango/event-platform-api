from rest_framework import serializers

from .models import Notification


class AdminNotificationSerializer(serializers.ModelSerializer):

    registration_number = serializers.CharField(
        source="registration.registration_number",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "registration",
            "registration_number",
            "channel",
            "notification_type",
            "recipient",
            "subject",
            "status",
            "error_message",
            "sent_at",
            "created_at",
        )
        read_only_fields = fields
