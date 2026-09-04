from django.urls import path

from .views import AdminEventNotificationListView, AdminNotificationResendView

urlpatterns = [

    path(
        "admin/events/<uuid:event_id>/notifications/",
        AdminEventNotificationListView.as_view(),
        name="admin-event-notification-list",
    ),
    path(
        "admin/events/<uuid:event_id>/notifications/<uuid:id>/resend/",
        AdminNotificationResendView.as_view(),
        name="admin-event-notification-resend",
    ),
]
