from apps.events.models import Event
from apps.organizations.models import Organization


ORGANIZATION_ADMIN_ROLES = {
    "OWNER",
    "ADMIN",
}


def get_user_organization_membership(
    user,
    organization_id,
):
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