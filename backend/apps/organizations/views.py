from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from .models import Organization
from .serializers import (
    OrganizationDetailSerializer,
    OrganizationListSerializer,
)


class OrganizationListView(ListAPIView):

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        OrganizationListSerializer
    )

    def get_queryset(self):

        if self.request.user.is_superuser:
            return Organization.objects.filter(is_active=True)

        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct()


class OrganizationDetailView(
    RetrieveAPIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        OrganizationDetailSerializer
    )

    lookup_url_kwarg = "organization_id"

    def get_queryset(self):

        if self.request.user.is_superuser:
            return Organization.objects.filter(is_active=True)

        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct()