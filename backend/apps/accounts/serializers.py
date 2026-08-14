from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSerializer(serializers.ModelSerializer):

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_superuser",
            "is_staff",
        )

class LoginSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):

        token = super().get_token(user)

        token["email"] = user.email
        token["full_name"] = user.full_name

        return token


class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField()

    def validate(self, attrs):

        self.token = RefreshToken(
            attrs["refresh"]
        )

        return attrs

    def save(self, **kwargs):

        self.token.blacklist()


class UpdateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
        )


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Full user representation for the admin Users page — includes active
    org memberships with role, the same shape MeView already builds for
    the calling user's own memberships (see apps/accounts/views.py).
    """

    full_name = serializers.ReadOnlyField()
    organization_memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_active",
            "is_superuser",
            "is_staff",
            "created_at",
            "organization_memberships",
        )
        read_only_fields = ("id", "created_at")

    def get_organization_memberships(self, user):
        return [
            {
                "id": membership.id,
                "organization_id": membership.organization_id,
                "organization_name": membership.organization.name,
                "role": membership.role,
                "is_active": membership.is_active,
            }
            for membership in (
                user.organization_memberships
                .filter(is_active=True)
                .select_related("organization")
            )
        ]


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    Superuser-only user creation (apps/accounts/views.py
    AdminUserCreateView). Optionally creates the user's first
    OrganizationMembership in the same call — organization_id and role
    must be given together or not at all.
    """

    password = serializers.CharField(write_only=True, min_length=8)

    organization_id = serializers.UUIDField(
        write_only=True, required=False
    )

    role = serializers.ChoiceField(
        choices=[],  # set in __init__ to avoid a circular import at module load
        write_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "is_superuser",
            "organization_id",
            "role",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.organizations.models import OrganizationMembership
        self.fields["role"].choices = OrganizationMembership.Role.choices

    def validate(self, attrs):
        if bool(attrs.get("organization_id")) != bool(attrs.get("role")):
            raise serializers.ValidationError(
                "organization_id and role must be provided together."
            )
        return attrs

    def create(self, validated_data):
        from apps.organizations.models import OrganizationMembership

        organization_id = validated_data.pop("organization_id", None)
        role = validated_data.pop("role", None)
        password = validated_data.pop("password")
        is_superuser = validated_data.get("is_superuser", False)

        user = User.objects.create_user(
            password=password,
            is_staff=is_superuser,
            **validated_data,
        )

        if organization_id:
            OrganizationMembership.objects.create(
                user=user,
                organization_id=organization_id,
                role=role,
            )

        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    Superuser-only profile/status edits (AdminUserDetailView.patch).
    Role/membership changes go through the organization/event membership
    endpoints instead, not here.
    """

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
            "is_active",
            "is_superuser",
        )


class ChangePasswordSerializer(serializers.Serializer):

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user