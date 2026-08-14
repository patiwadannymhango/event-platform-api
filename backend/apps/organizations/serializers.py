# from rest_framework import serializers


# class EventSummarySerializer(serializers.Serializer):

#     id = serializers.UUIDField()

#     name = serializers.CharField()

#     slug = serializers.CharField()

#     status = serializers.CharField()


# class OrganizationContextSerializer(serializers.Serializer):

#     id = serializers.UUIDField()

#     name = serializers.CharField()

#     slug = serializers.CharField()

#     role = serializers.CharField()

#     events = EventSummarySerializer(
#         many=True
#     )


from rest_framework import serializers

from .models import Organization, OrganizationMembership


class OrganizationListSerializer(
    serializers.ModelSerializer
):

    role = serializers.CharField(
        read_only=True
    )

    class Meta:
        model = Organization

        fields = (
            "id",
            "name",
            "slug",
            "description",
            "email",
            "phone",
            "website",
            "role",
        )


class OrganizationDetailSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = Organization

        fields = (
            "id",
            "name",
            "slug",
            "description",
            "email",
            "phone",
            "website",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class OrganizationWriteSerializer(serializers.ModelSerializer):
    """Create/update — superuser creates, org OWNER/ADMIN (or superuser) updates."""

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "email",
            "phone",
            "website",
            "is_active",
        )
        read_only_fields = ("id",)


class OrganizationMembershipSerializer(serializers.ModelSerializer):

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMembership
        fields = (
            "id",
            "user",
            "user_email",
            "user_full_name",
            "organization",
            "role",
            "is_active",
        )
        read_only_fields = ("id", "organization", "user_email", "user_full_name")

    def get_user_full_name(self, membership):
        return membership.user.full_name


class OrganizationMembershipWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganizationMembership
        fields = ("user", "role")