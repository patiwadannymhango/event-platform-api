from rest_framework import serializers

from .models import Participant


class AdminParticipantSerializer(serializers.ModelSerializer):

    registration_count = serializers.IntegerField(
        source="registrations.count", read_only=True
    )

    class Meta:
        model = Participant
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "registration_count",
            "created_at",
        )
        read_only_fields = fields
