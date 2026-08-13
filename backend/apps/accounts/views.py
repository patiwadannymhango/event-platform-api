from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from rest_framework.permissions import IsAuthenticated

from .serializers import LogoutSerializer

from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
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