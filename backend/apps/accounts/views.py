from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.permissions import IsSuperUser

from .models import User
from .serializers import (
    AdminUserCreateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):

    permission_classes = [
        AllowAny,
    ]

    serializer_class = LoginSerializer


class LogoutView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):

        serializer = LogoutSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            {
                "detail": "Successfully logged out."
            },
            status=status.HTTP_205_RESET_CONTENT,
        )

class MeView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        user = request.user

        organizations = []

        memberships = (
            user.organization_memberships
            .filter(is_active=True)
            .select_related("organization")
        )

        for membership in memberships:

            organization = membership.organization

            events = (
                organization.events
                .filter(is_active=True)
                .order_by("start_date")
            )

            event_memberships = {
                membership.event_id: membership
                for membership in (
                    user.event_memberships
                    .filter(
                        is_active=True,
                        event__organization=organization,
                    )
                )
            }

            event_data = []

            for event in events:

                organization_role = membership.role

                event_membership = (
                    event_memberships.get(
                        event.id
                    )
                )

                event_data.append(
                    {
                        "id": event.id,
                        "name": event.name,
                        "slug": event.slug,
                        "status": event.status,
                        "role": (
                            event_membership.role
                            if event_membership
                            else organization_role
                        ),
                    }
                )

            organizations.append(
                {
                    "id": organization.id,
                    "name": organization.name,
                    "slug": organization.slug,
                    "role": membership.role,
                    "events": event_data,
                }
            )

        return Response(
            {
                "user": UserSerializer(user).data,
                "organizations": organizations,
            }
        )

    def patch(self, request):
        serializer = UpdateProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})


# ---------------------------------------------------------------------------
# Admin-facing views — superuser-only user management. There is no
# self-registration or org-scoped invite flow yet; only a superuser can
# create accounts (org owners/admins assign roles to already-existing
# users via the organization/event membership endpoints instead).
# ---------------------------------------------------------------------------


class AdminUserListView(generics.ListAPIView):

    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = AdminUserSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["created_at", "email"]
    queryset = User.objects.all().order_by("-created_at")


class AdminUserCreateView(APIView):

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            AdminUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class AdminUserDetailView(APIView):
    """
    GET/PATCH/DELETE /api/v1/auth/admin/users/<user_id>/

    DELETE deactivates (is_active=False) rather than hard-deleting, since
    a user can be the requested_by/created_by on other records.
    """

    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        return Response(AdminUserSerializer(user).data)

    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = AdminUserUpdateSerializer(
            user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserSerializer(user).data)

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)