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

from .models import Organization


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