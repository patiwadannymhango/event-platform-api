from django.contrib import admin

from .models import (
    Organization,
    OrganizationMembership,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "email",
        "phone",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "organization",
        "role",
        "is_active",
    )

    list_filter = (
        "role",
        "is_active",
        "organization",
    )

    search_fields = (
        "user__email",
        "organization__name",
    )