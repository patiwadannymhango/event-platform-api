from rest_framework import serializers

from .models import Event


class EventListSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = Event

        fields = (
            "id",
            "name",
            "slug",
            "description",
            "start_date",
            "end_date",
            "location",
            "status",
            "is_active",
        )


class EventDetailSerializer(
    serializers.ModelSerializer
):

    organization = serializers.UUIDField(
        source="organization_id",
        read_only=True,
    )

    class Meta:
        model = Event

        fields = (
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "start_date",
            "end_date",
            "location",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )