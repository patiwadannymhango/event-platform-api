from django.contrib import admin

from .models import (
    Registration,
    RegistrationCategory,
    RegistrationField,
    RegistrationForm,
)


@admin.register(RegistrationForm)
class RegistrationFormAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "event",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "event__name",
    )


@admin.register(RegistrationField)
class RegistrationFieldAdmin(admin.ModelAdmin):

    list_display = (
        "label",
        "form",
        "field_type",
        "is_required",
        "display_order",
        "is_active",
    )

    list_filter = (
        "field_type",
        "is_required",
        "is_active",
    )

    search_fields = (
        "label",
        "key",
        "form__event__name",
    )

    ordering = (
        "form",
        "display_order",
    )


@admin.register(RegistrationCategory)
class RegistrationCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "event",
        "price",
        "currency",
        "capacity",
        "is_active",
    )

    list_filter = (
        "currency",
        "is_active",
        "event",
    )

    search_fields = (
        "name",
        "code",
        "event__name",
    )


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):

    list_display = (
        "registration_number",
        "participant",
        "event",
        "category",
        "status",
        "amount",
        "currency",
        "registered_at",
    )

    list_filter = (
        "status",
        "event",
        "category",
        "currency",
    )

    search_fields = (
        "registration_number",
        "participant__first_name",
        "participant__last_name",
        "participant__email",
        "participant__phone",
    )

    readonly_fields = (
        "registration_number",
        "registered_at",
        "updated_at",
    )