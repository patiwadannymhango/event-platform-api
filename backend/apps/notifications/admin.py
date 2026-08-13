from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "channel",
        "notification_type",
        "status",
        "registration",
        "created_at",
    )

    list_filter = (
        "channel",
        "status",
        "notification_type",
    )

    search_fields = (
        "recipient",
        "subject",
        "registration__registration_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "sent_at",
    )
