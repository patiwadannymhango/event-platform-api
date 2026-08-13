from django.contrib import admin

from .models import (
    Event,
    EventMembership,
)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "status",
        "start_date",
        "is_active",
    )

    list_filter = (
        "status",
        "organization",
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
        "location",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(EventMembership)
class EventMembershipAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "event",
        "role",
        "is_active",
    )

    list_filter = (
        "role",
        "event",
        "is_active",
    )

    search_fields = (
        "user__email",
        "event__name",
    )