from django.contrib import admin
from django.urls import include
from django.urls import path


urlpatterns = [

    # Not "admin/" — in the single-origin deployment that path would sit
    # next to the React admin dashboard at /dashboard and read as the same
    # thing. This is Django's own admin site.
    path(
        "django-admin/",
        admin.site.urls,
    ),

    path(
        "api/v1/auth/",
        include(
            "apps.accounts.urls"
        ),
    ),

    path(
        "api/v1/organizations/",
        include(
            "apps.organizations.urls"
        ),
    ),
    path(
        "api/v1/events/",
        include(
            "apps.events.urls"
        ),
    ),
    path(
        "api/v1/registrations/",
        include(
            "apps.registrations.urls"
        ),
    ),
    path(
        "api/v1/payments/",
        include(
            "apps.payments.urls"
        ),
    ),
    path(
        "api/v1/participants/",
        include(
            "apps.participants.urls"
        ),
    ),
    path(
        "api/v1/notifications/",
        include(
            "apps.notifications.urls"
        ),
    ),
]