from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)

from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasOrganizationRole, IsSuperUser

from .models import Organization, OrganizationMembership
from .serializers import (
    OrganizationDetailSerializer,
    OrganizationListSerializer,
    OrganizationMembershipSerializer,
    OrganizationMembershipWriteSerializer,
    OrganizationWriteSerializer,
)


class OrganizationListView(ListAPIView):
    """
    GET lists orgs the caller belongs to (or all, for a superuser).
    POST creates a new organization — superuser only, since creating an
    org is a platform-level action with no owner assigned yet.
    """

    serializer_class = (
        OrganizationListSerializer
    )

    def get_permissions(self):
        classes = (
            [IsAuthenticated, IsSuperUser]
            if self.request.method == "POST"
            else [IsAuthenticated]
        )
        return [cls() for cls in classes]

    def get_queryset(self):

        if self.request.user.is_superuser:
            return Organization.objects.filter(is_active=True)

        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct()

    def post(self, request):
        serializer = OrganizationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.save()
        return Response(
            OrganizationDetailSerializer(organization).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationDetailView(
    RetrieveAPIView
):
    """
    GET is open to any member (or superuser). PATCH/DELETE require
    OWNER/ADMIN (or superuser) — DELETE deactivates rather than
    hard-deleting, since events/registrations/payments hang off an org.
    """

    serializer_class = (
        OrganizationDetailSerializer
    )

    lookup_url_kwarg = "organization_id"

    def get_permissions(self):
        classes = (
            [IsAuthenticated]
            if self.request.method == "GET"
            else [IsAuthenticated, HasOrganizationRole("OWNER", "ADMIN")]
        )
        return [cls() for cls in classes]

    def get_queryset(self):

        if self.request.user.is_superuser:
            return Organization.objects.filter(is_active=True)

        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct()

    def patch(self, request, organization_id):
        organization = get_object_or_404(
            self.get_queryset(), id=organization_id
        )
        serializer = OrganizationWriteSerializer(
            organization, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrganizationDetailSerializer(organization).data)

    def delete(self, request, organization_id):
        organization = get_object_or_404(
            self.get_queryset(), id=organization_id
        )
        organization.is_active = False
        organization.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationMembershipListCreateView(APIView):
    """
    GET/POST /api/v1/organizations/<organization_id>/members/

    OWNER/ADMIN (or superuser) only. POST re-activates and updates the
    role if the user already has a (possibly deactivated) membership row
    for this org, rather than erroring on the unique constraint.
    """

    def get_permissions(self):
        return [
            IsAuthenticated(),
            HasOrganizationRole("OWNER", "ADMIN")(),
        ]

    def get(self, request, organization_id):
        memberships = (
            OrganizationMembership.objects
            .filter(organization_id=organization_id)
            .select_related("user", "organization")
        )
        return Response(
            OrganizationMembershipSerializer(memberships, many=True).data
        )

    def post(self, request, organization_id):
        serializer = OrganizationMembershipWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership, _ = OrganizationMembership.objects.update_or_create(
            user=serializer.validated_data["user"],
            organization_id=organization_id,
            defaults={
                "role": serializer.validated_data["role"],
                "is_active": True,
            },
        )

        return Response(
            OrganizationMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationMembershipDetailView(APIView):
    """PATCH role / DELETE (=deactivate) a single membership."""

    def get_permissions(self):
        return [
            IsAuthenticated(),
            HasOrganizationRole("OWNER", "ADMIN")(),
        ]

    def patch(self, request, organization_id, membership_id):
        membership = get_object_or_404(
            OrganizationMembership,
            id=membership_id,
            organization_id=organization_id,
        )
        serializer = OrganizationMembershipWriteSerializer(
            membership, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrganizationMembershipSerializer(membership).data)

    def delete(self, request, organization_id, membership_id):
        membership = get_object_or_404(
            OrganizationMembership,
            id=membership_id,
            organization_id=organization_id,
        )
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)