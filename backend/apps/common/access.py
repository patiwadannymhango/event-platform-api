from apps.events.models import Event
from apps.organizations.models import Organization


ORGANIZATION_ADMIN_ROLES = {
    "OWNER",
    "ADMIN",
}

# Role tiers for the admin endpoints in apps/payments and
# apps/registrations. A role string here may come from either
# OrganizationMembership.role (OWNER/ADMIN/FINANCE/REGISTRATION/
# EVENT_MANAGER/VIEWER, bubbling down via user_event_role) or
# EventMembership.role (ADMIN/FINANCE/REGISTRATION/VIEWER) — these tiers
# cover whichever vocabulary the caller's role actually came from.
EVENT_VIEW_ROLES = (
    "OWNER",
    "ADMIN",
    "FINANCE",
    "REGISTRATION",
    "EVENT_MANAGER",
    "VIEWER",
)

EVENT_REGISTRATION_MANAGE_ROLES = (
    "OWNER",
    "ADMIN",
    "EVENT_MANAGER",
    "REGISTRATION",
)

EVENT_FINANCE_ROLES = (
    "OWNER",
    "ADMIN",
    "FINANCE",
)

# Role strings that indicate admin-level control of an event (native
# EventMembership "ADMIN", or an org OWNER/ADMIN role bubbling down) —
# used to gate managing an event's own memberships.
EVENT_ADMIN_ROLES = (
    "OWNER",
    "ADMIN",
)


def get_user_organization_membership(
    user,
    organization_id,
):
    """
    Returns the caller's real membership row, or None — including for a
    superuser with no explicit membership. Superusers get full access via
    user_has_organization_access/user_has_event_access below regardless
    of what this returns; callers that need an actual role string (e.g.
    to display "your role") should treat None from a superuser as
    "OWNER-equivalent", not "no access".
    """

    return (
        user.organization_memberships
        .filter(
            organization_id=organization_id,
            is_active=True,
        )
        .select_related("organization")
        .first()
    )


def user_has_organization_access(
    user,
    organization_id,
):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.organization_memberships.filter(
        organization_id=organization_id,
        is_active=True,
    ).exists()


def user_has_event_access(
    user,
    event_id,
):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    event = (
        Event.objects
        .select_related("organization")
        .filter(
            id=event_id,
            is_active=True,
        )
        .first()
    )

    if not event:
        return False

    organization_membership = (
        user.organization_memberships
        .filter(
            organization=event.organization,
            is_active=True,
        )
        .first()
    )

    if organization_membership:
        if organization_membership.role in (
            ORGANIZATION_ADMIN_ROLES
        ):
            return True

    return user.event_memberships.filter(
        event=event,
        is_active=True,
    ).exists()


def user_organization_role(
    user,
    organization_id,
):
    """
    Effective org role string for `user`, or None if they have no access.
    A superuser always resolves to "OWNER" (full access) even with no
    real membership row.
    """

    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return "OWNER"

    membership = get_user_organization_membership(
        user,
        organization_id,
    )

    return membership.role if membership else None


def user_event_role(
    user,
    event_id,
):
    """
    Effective event role string for `user`, or None. Mirrors MeView's
    resolution: an explicit EventMembership role wins, otherwise an
    org OWNER/ADMIN role bubbles down (matches user_has_event_access), so
    an org admin doesn't need a separate EventMembership row to manage
    every event in their org. A superuser always resolves to "ADMIN".
    """

    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return "ADMIN"

    event = (
        Event.objects
        .select_related("organization")
        .filter(id=event_id, is_active=True)
        .first()
    )

    if not event:
        return None

    organization_membership = get_user_organization_membership(
        user,
        event.organization_id,
    )

    if (
        organization_membership
        and organization_membership.role in ORGANIZATION_ADMIN_ROLES
    ):
        return organization_membership.role

    event_membership = user.event_memberships.filter(
        event=event,
        is_active=True,
    ).first()

    return event_membership.role if event_membership else None


def require_organization_role(user, organization_id, *roles):
    """
    Raises DRF's PermissionDenied unless `user`'s effective org role is
    one of `roles`. For views that fetch their object first (e.g. an
    admin view keyed by payment_id, not organization_id) rather than
    having the id available as a URL kwarg a permission class can read —
    same manual-check pattern EventDetailView.get_object() already uses.
    """

    from rest_framework.exceptions import PermissionDenied

    if user_organization_role(user, organization_id) not in roles:
        raise PermissionDenied(
            "You do not have the required role for this organization."
        )


def require_event_role(user, event_id, *roles):
    """Same as require_organization_role, for event-scoped roles."""

    from rest_framework.exceptions import PermissionDenied

    if user_event_role(user, event_id) not in roles:
        raise PermissionDenied(
            "You do not have the required role for this event."
        )