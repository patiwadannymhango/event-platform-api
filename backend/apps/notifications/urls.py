from django.urls import path

from .views import AdminEventNotificationListView

urlpatterns = [

    path(
        "admin/events/<uuid:event_id>/notifications/",
        AdminEventNotificationListView.as_view(),
        name="admin-event-notification-list",
    ),
]
