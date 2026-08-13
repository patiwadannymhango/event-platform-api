from rest_framework.permissions import BasePermission

from .access import (
    user_has_event_access,
    user_has_organization_access,
)


class IsAuthenticatedUser(BasePermission):

    message = "Authentication is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )


class IsOrganizationMember(BasePermission):

    message = (
        "You do not have access to this organization."
    )

    def has_permission(self, request, view):

        organization_id = view.kwargs.get(
            "organization_id"
        )

        if not organization_id:
            return False

        return user_has_organization_access(
            request.user,
            organization_id,
        )


class IsEventMember(BasePermission):

    message = (
        "You do not have access to this event."
    )

    def has_permission(self, request, view):

        event_id = view.kwargs.get(
            "event_id"
        )

        if not event_id:
            return False

        return user_has_event_access(
            request.user,
            event_id,
        )