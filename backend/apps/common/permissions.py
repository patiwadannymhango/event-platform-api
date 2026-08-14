from rest_framework.permissions import BasePermission

from .access import (
    user_event_role,
    user_has_event_access,
    user_has_organization_access,
    user_organization_role,
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


class IsSuperUser(BasePermission):

    message = "This action requires superuser access."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


def HasOrganizationRole(*roles):
    """
    Factory for a permission class requiring the caller's effective
    organization role (see access.user_organization_role — a superuser
    always qualifies) to be one of `roles`, resolved from
    view.kwargs["organization_id"]. For views not keyed by
    organization_id (e.g. an admin view keyed by payment_id instead),
    this permission class has nothing to check at the URL level and
    passes through — use access.require_organization_role inside the
    view after fetching the object instead.

    Usage: permission_classes = [IsAuthenticated, HasOrganizationRole("OWNER", "ADMIN")]
    """

    class _HasOrganizationRole(BasePermission):

        message = (
            "Requires one of these organization roles: "
            + ", ".join(roles)
        )

        def has_permission(self, request, view):

            organization_id = view.kwargs.get("organization_id")

            if not organization_id:
                return True

            return user_organization_role(
                request.user,
                organization_id,
            ) in roles

    return _HasOrganizationRole


def HasEventRole(*roles):
    """
    Same as HasOrganizationRole, but for view.kwargs["event_id"] and
    access.user_event_role (which already bubbles down an org OWNER/ADMIN
    role, matching user_has_event_access).
    """

    class _HasEventRole(BasePermission):

        message = (
            "Requires one of these event roles: "
            + ", ".join(roles)
        )

        def has_permission(self, request, view):

            event_id = view.kwargs.get("event_id")

            if not event_id:
                return True

            return user_event_role(
                request.user,
                event_id,
            ) in roles

    return _HasEventRole