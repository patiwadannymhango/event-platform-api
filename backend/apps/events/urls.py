from django.urls import path

from .views import (
    EventDetailView,
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
]