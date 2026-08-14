from django.urls import path

from .views import AdminEventParticipantListView

urlpatterns = [

    path(
        "admin/events/<uuid:event_id>/participants/",
        AdminEventParticipantListView.as_view(),
        name="admin-event-participant-list",
    ),
]
