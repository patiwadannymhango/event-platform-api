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

    # A free category (price 0 — e.g. an "Official Sponsor" entry) has
    # nothing to pay, and payments can't process a K0 charge anyway, so
    # it goes straight to CONFIRMED instead of waiting on a payment that
    # will never come.
    if category.price <= 0:
        status = Registration.Status.CONFIRMED
    elif reserve:
        status = Registration.Status.RESERVED
    else:
        status = Registration.Status.PENDING_PAYMENT

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

    if status == Registration.Status.CONFIRMED:
        from apps.notifications.services import (
            notify_payment_confirmed,
        )

        notify_payment_confirmed(registration)
    else:
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

    # Scanning every existing number for the max (rather than trusting the
    # most-recently-registered row) means a single malformed/blank
    # registration_number can't get "stuck" as the reference point and
    # keep producing the same already-taken number on every subsequent
    # attempt.
    #
    # Scoped by prefix match rather than by event: registration_number is
    # globally unique (not unique-per-event), and two events can easily
    # end up with the same 6-character prefix (e.g. "copperbelt-marathon-
    # 2026" and "copperbelt-marathon-2026-vendors" both truncate to
    # "COPPER") — scanning only this event's own registrations would find
    # zero and confidently hand out an already-taken number the moment a
    # second event shares a prefix.
    last_number = 0

    existing_numbers = (
        Registration.objects
        .filter(registration_number__startswith=f"{prefix}-")
        .values_list("registration_number", flat=True)
    )

    for registration_number in existing_numbers:
        try:
            number = int(
                registration_number
                .rsplit("-", 1)[-1]
            )
        except (
            ValueError,
            IndexError,
        ):
            continue

        last_number = max(last_number, number)

    next_number = last_number + 1

    return (
        f"{prefix}-"
        f"{next_number:06d}"
    )