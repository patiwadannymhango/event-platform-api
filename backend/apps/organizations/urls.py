from django.urls import path

from .views import (
    OrganizationDetailView,
    OrganizationListView,
    OrganizationMembershipDetailView,
    OrganizationMembershipListCreateView,
)

urlpatterns = [

    path(
        "",
        OrganizationListView.as_view(),
        name="organization-list",
    ),

    path(
        "<uuid:organization_id>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),

    path(
        "<uuid:organization_id>/members/",
        OrganizationMembershipListCreateView.as_view(),
        name="organization-membership-list",
    ),
    path(
        "<uuid:organization_id>/members/<uuid:membership_id>/",
        OrganizationMembershipDetailView.as_view(),
        name="organization-membership-detail",
    ),
]