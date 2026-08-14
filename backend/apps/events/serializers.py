from rest_framework import serializers

from .models import Event, EventMembership


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


class EventWriteSerializer(serializers.ModelSerializer):
    """
    Create/update. `organization` is required on create (an event has to
    belong to some org) but not writable on update — an event doesn't
    move between organizations.
    """

    class Meta:
        model = Event
        fields = (
            "id",
            "organization",
            "payment_account",
            "name",
            "slug",
            "description",
            "start_date",
            "end_date",
            "location",
            "status",
            "is_active",
        )
        read_only_fields = ("id",)

    def update(self, instance, validated_data):
        validated_data.pop("organization", None)
        return super().update(instance, validated_data)


class EventMembershipSerializer(serializers.ModelSerializer):

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = EventMembership
        fields = (
            "id",
            "user",
            "user_email",
            "user_full_name",
            "event",
            "role",
            "is_active",
        )
        read_only_fields = ("id", "event", "user_email", "user_full_name")

    def get_user_full_name(self, membership):
        return membership.user.full_name


class EventMembershipWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventMembership
        fields = ("user", "role")