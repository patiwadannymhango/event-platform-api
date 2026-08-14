from django.urls import path

from .views import (
    EventDetailView,
    EventMembershipDetailView,
    EventMembershipListCreateView,
    OrganizationEventListView,
)


urlpatterns = [

    path(
        "organization/<uuid:organization_id>/",
        OrganizationEventListView.as_view(),
        name="organization-event-list",
    ),

    path(
        "<uuid:event_id>/",
        EventDetailView.as_view(),
        name="event-detail",
    ),

    path(
        "<uuid:event_id>/members/",
        EventMembershipListCreateView.as_view(),
        name="event-membership-list",
    ),
    path(
        "<uuid:event_id>/members/<uuid:membership_id>/",
        EventMembershipDetailView.as_view(),
        name="event-membership-detail",
    ),
]