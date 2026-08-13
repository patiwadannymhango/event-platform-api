"""
High-level "tell the runner what just happened" functions. These are the
functions the rest of the codebase (registration/payment services,
webhooks, admin actions) should call — they know how to compose the
message and fire both email + SMS where appropriate.
"""

from .email import send_email
from .sms import send_sms
from .models import Notification


def _participant_contact(registration):
    participant = registration.participant
    return participant.email, participant.phone


def notify_registration_received(registration, *, reserved=False):
    email, phone = _participant_contact(registration)
    participant = registration.participant

    if reserved:
        subject = f"Spot reserved — {registration.registration_number}"
        text = (
            f"Hi {participant.first_name},\n\n"
            f"Your spot for {registration.event.name} is reserved.\n"
            f"Reference: {registration.registration_number}\n"
            f"Category: {registration.category.name}\n"
            f"Amount due: {registration.currency} {registration.amount}\n\n"
            "Your spot is held for a limited time — complete payment to "
            "confirm it. Reply to this email if you have questions.\n"
        )
        notification_type = Notification.NotificationType.RESERVATION_CONFIRMED
    else:
        subject = f"Registration received — {registration.registration_number}"
        text = (
            f"Hi {participant.first_name},\n\n"
            f"We've received your registration for {registration.event.name}.\n"
            f"Reference: {registration.registration_number}\n"
            f"Category: {registration.category.name}\n"
            f"Amount due: {registration.currency} {registration.amount}\n\n"
            "Complete payment to confirm your place.\n"
        )
        notification_type = Notification.NotificationType.REGISTRATION_RECEIVED

    if email:
        send_email(
            to=email,
            subject=subject,
            text_body=text,
            registration=registration,
            notification_type=notification_type,
        )

    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=notification_type,
        )


def notify_payment_confirmed(registration):
    email, phone = _participant_contact(registration)
    participant = registration.participant

    subject = f"Payment confirmed — {registration.registration_number}"
    text = (
        f"Hi {participant.first_name},\n\n"
        f"Your payment for {registration.event.name} is confirmed. "
        f"You're all set for race day!\n"
        f"Reference: {registration.registration_number}\n"
        f"Category: {registration.category.name}\n"
        f"Amount paid: {registration.currency} {registration.amount}\n\n"
        "See you at the start line.\n"
    )

    if email:
        send_email(
            to=email,
            subject=subject,
            text_body=text,
            registration=registration,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
        )

    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
        )


def notify_payment_failed(registration, *, reason=""):
    email, phone = _participant_contact(registration)
    participant = registration.participant

    subject = f"Payment issue — {registration.registration_number}"
    text = (
        f"Hi {participant.first_name},\n\n"
        f"We couldn't confirm your payment for {registration.event.name}"
        f"{f' ({reason})' if reason else ''}.\n"
        f"Reference: {registration.registration_number}\n\n"
        "Please try again, or contact us for help.\n"
    )

    if email:
        send_email(
            to=email,
            subject=subject,
            text_body=text,
            registration=registration,
            notification_type=Notification.NotificationType.PAYMENT_FAILED,
        )

    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=Notification.NotificationType.PAYMENT_FAILED,
        )


def notify_refund_processed(registration, *, amount):
    email, phone = _participant_contact(registration)
    participant = registration.participant

    subject = f"Refund processed — {registration.registration_number}"
    text = (
        f"Hi {participant.first_name},\n\n"
        f"A refund of {registration.currency} {amount} has been processed "
        f"for your registration {registration.registration_number}.\n"
    )

    if email:
        send_email(
            to=email,
            subject=subject,
            text_body=text,
            registration=registration,
            notification_type=Notification.NotificationType.REFUND_PROCESSED,
        )

    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=Notification.NotificationType.REFUND_PROCESSED,
        )
