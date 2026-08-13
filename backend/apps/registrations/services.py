from django.db import transaction

from apps.participants.models import Participant

from .models import Registration


@transaction.atomic
def create_registration(
    *,
    event,
    category,
    participant_data,
    form_data,
    reserve=False,
):

    participant = Participant.objects.create(
        first_name=participant_data[
            "first_name"
        ],
        last_name=participant_data[
            "last_name"
        ],
        email=participant_data.get(
            "email",
            "",
        ),
        phone=participant_data.get(
            "phone",
            "",
        ),
        date_of_birth=participant_data.get(
            "date_of_birth"
        ),
        gender=participant_data.get(
            "gender",
            "",
        ),
    )

    status = (
        Registration.Status.RESERVED
        if reserve
        else Registration.Status.PENDING_PAYMENT
    )

    registration = Registration.objects.create(
        participant=participant,
        event=event,
        category=category,
        registration_number=(
            generate_registration_number(
                event
            )
        ),
        status=status,
        amount=category.price,
        currency=category.currency,
        form_data=form_data,
    )

    from apps.notifications.services import (
        notify_registration_received,
    )

    notify_registration_received(
        registration,
        reserved=reserve,
    )

    return registration


def generate_registration_number(
    event,
):

    prefix = (
        event.slug
        .replace("-", "")
        .upper()[:6]
    )

    last_registration = (
        Registration.objects
        .filter(event=event)
        .order_by("-registered_at")
        .first()
    )

    if last_registration:
        try:
            last_number = int(
                last_registration
                .registration_number
                .split("-")[-1]
            )
        except (
            ValueError,
            IndexError,
        ):
            last_number = 0
    else:
        last_number = 0

    next_number = last_number + 1

    return (
        f"{prefix}-"
        f"{next_number:06d}"
    )