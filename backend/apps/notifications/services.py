"""
High-level "tell the runner what just happened" functions. These are the
functions the rest of the codebase (registration/payment services,
webhooks, admin actions) should call — they know how to compose the
message and fire both email + SMS where appropriate.

Normally only one email goes to a runner for the whole registration
lifecycle: the "registration confirmed" email in notify_payment_confirmed(),
sent once the registration actually succeeds (payment settles, or an admin
marks it CONFIRMED). The other automatic notify_* functions below
intentionally do not send email — no "registration received" email while
payment is still pending, and no failure/refund emails — by design, so a
runner never receives more than one email out of that automatic flow.

notify_registration_received_email() is the one deliberate exception —
never called automatically, only from an admin action for registrations
that are being paid for by someone else (a sponsor/company), where there's
no payment step for the runner to eventually get an email about.
"""

from django.conf import settings
from django.template.loader import render_to_string

from .email import send_email
from .sms import send_sms
from .models import Notification


def _participant_contact(registration):
    participant = registration.participant
    return participant.email, participant.phone


def notify_registration_received(registration, *, reserved=False):
    _, phone = _participant_contact(registration)
    participant = registration.participant

    if reserved:
        text = (
            f"Hi {participant.first_name},\n\n"
            f"Your spot for {registration.event.name} is reserved.\n"
            f"Reference: {registration.registration_number}\n"
            f"Category: {registration.category.name}\n"
            f"Amount due: {registration.currency} {registration.amount}\n\n"
            "Your spot is held for a limited time — complete payment to "
            "confirm it.\n"
        )
        notification_type = Notification.NotificationType.RESERVATION_CONFIRMED
    else:
        text = (
            f"Hi {participant.first_name},\n\n"
            f"We've received your registration for {registration.event.name}.\n"
            f"Reference: {registration.registration_number}\n"
            f"Category: {registration.category.name}\n"
            f"Amount due: {registration.currency} {registration.amount}\n\n"
            "Complete payment to confirm your place.\n"
        )
        notification_type = Notification.NotificationType.REGISTRATION_RECEIVED

    # Deliberately no email here — see module docstring. The runner's one
    # email arrives once the registration actually succeeds.
    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=notification_type,
        )


def _build_registration_received_email(registration):
    """Composes the (subject, text, html) for the sponsor-paid "you're
    registered" email — shared by the automatic send and a later resend,
    so a resend always reflects the registration's current data rather
    than a stale snapshot."""
    participant = registration.participant
    event = registration.event

    subject = f"You're registered — {registration.registration_number}"
    text = (
        f"Hi {participant.first_name},\n\n"
        f"Thanks for registering for {event.name}. Your spot is reserved "
        "— see you at the start line!\n\n"
        f"Reference: {registration.registration_number}\n"
        f"Race category: {registration.category.name}\n"
        + (f"Event date: {event.start_date:%d %B %Y}\n" if event.start_date else "")
        + (f"Venue: {event.location}\n" if event.location else "")
    )

    logo_url = (
        f"{settings.PUBLIC_BASE_URL}/static/notifications/email/logo.png"
        if settings.PUBLIC_BASE_URL
        else ""
    )
    track_url = (
        f"{settings.PUBLIC_SITE_URL}/#track" if settings.PUBLIC_SITE_URL else "#"
    )

    html = render_to_string(
        "notifications/emails/registration_pending.html",
        {
            "first_name": participant.first_name,
            "event_name": event.name,
            "reference": registration.registration_number,
            "category_name": registration.category.name,
            "event_date": f"{event.start_date:%d %B %Y}" if event.start_date else "",
            "event_location": event.location,
            "logo_url": logo_url,
            "track_url": track_url,
            "contact_email": settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    return subject, text, html


def notify_registration_received_email(registration):
    """
    Email-only "you're registered" notification, with no payment language
    at all — for registrations someone else is paying for (a sponsor/
    company covering a team's entry fees), where the runner has no
    payment step of their own to eventually get an email about. Not
    wired into any automatic flow; call this explicitly from an admin
    action when that's actually the situation.
    """
    email, _ = _participant_contact(registration)
    if not email:
        return

    subject, text, html = _build_registration_received_email(registration)

    send_email(
        to=email,
        subject=subject,
        text_body=text,
        html_body=html,
        registration=registration,
        notification_type=Notification.NotificationType.REGISTRATION_RECEIVED,
    )


def _build_payment_confirmed_email(registration):
    """Composes the (subject, text, html) for the "you're confirmed"
    email — shared by the automatic send and a later resend, so a resend
    always reflects the registration's current data rather than a stale
    snapshot."""
    participant = registration.participant
    event = registration.event

    subject = f"You're confirmed — {registration.registration_number}"
    text = (
        f"Hi {participant.first_name},\n\n"
        f"Your entry for {event.name} is confirmed and paid. This email is "
        "your proof of registration — keep it handy for race pack "
        "collection.\n\n"
        f"Reference: {registration.registration_number}\n"
        f"Race category: {registration.category.name}\n"
        f"Amount paid: {registration.currency} {registration.amount}\n"
        + (f"Event date: {event.start_date:%d %B %Y}\n" if event.start_date else "")
        + (f"Venue: {event.location}\n" if event.location else "")
        + "\nOn race day, bring a valid ID and this reference number to "
        "collect your race pack.\n\n"
        "See you at the start line.\n"
    )

    logo_url = (
        f"{settings.PUBLIC_BASE_URL}/static/notifications/email/logo.png"
        if settings.PUBLIC_BASE_URL
        else ""
    )
    track_url = (
        f"{settings.PUBLIC_SITE_URL}/#track" if settings.PUBLIC_SITE_URL else "#"
    )

    html = render_to_string(
        "notifications/emails/registration_confirmed.html",
        {
            "first_name": participant.first_name,
            "event_name": event.name,
            "reference": registration.registration_number,
            "category_name": registration.category.name,
            "currency": registration.currency,
            "amount": registration.amount,
            "event_date": f"{event.start_date:%d %B %Y}" if event.start_date else "",
            "event_location": event.location,
            "logo_url": logo_url,
            "track_url": track_url,
            "contact_email": settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    return subject, text, html


def notify_payment_confirmed(registration):
    """The one email a runner gets: sent once the registration actually
    succeeds — a real payment settling, or an admin marking it CONFIRMED."""
    email, phone = _participant_contact(registration)
    subject, text, html = _build_payment_confirmed_email(registration)

    if email:
        send_email(
            to=email,
            subject=subject,
            text_body=text,
            html_body=html,
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
    _, phone = _participant_contact(registration)
    participant = registration.participant

    text = (
        f"Hi {participant.first_name},\n\n"
        f"We couldn't confirm your payment for {registration.event.name}"
        f"{f' ({reason})' if reason else ''}.\n"
        f"Reference: {registration.registration_number}\n\n"
        "Please try again, or contact us for help.\n"
    )

    # Deliberately no email here — see module docstring.
    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=Notification.NotificationType.PAYMENT_FAILED,
        )


def notify_refund_processed(registration, *, amount):
    _, phone = _participant_contact(registration)
    participant = registration.participant

    text = (
        f"Hi {participant.first_name},\n\n"
        f"A refund of {registration.currency} {amount} has been processed "
        f"for your registration {registration.registration_number}.\n"
    )

    # Deliberately no email here — see module docstring.
    if phone:
        send_sms(
            to=phone,
            message=text,
            registration=registration,
            notification_type=Notification.NotificationType.REFUND_PROCESSED,
        )


# Notification types that have a template to regenerate from live
# registration data, keyed to the builder that produces (subject, text,
# html) for them. Anything else falls back to replaying the plain-text
# body that was actually logged at send time (see resend_notification_email).
_RESENDABLE_EMAIL_BUILDERS = {
    Notification.NotificationType.PAYMENT_CONFIRMED: _build_payment_confirmed_email,
    Notification.NotificationType.REGISTRATION_RECEIVED: _build_registration_received_email,
}


def resend_notification_email(notification, *, to):
    """
    Re-sends a previously logged email — to `to`, which may be the
    notification's original recipient or a corrected address an admin
    typed in (the usual reason to resend is that the first address
    bounced or was mistyped). For notification types with a known
    template, the email is rebuilt from the registration's current data
    (so a resend after an amount/category correction reflects reality,
    not what it was at original send time); anything else falls back to
    resending exactly what was logged, as plain text.

    Always creates a new Notification row — resending doesn't rewrite the
    original log entry, it adds another attempt to the trail. Returns
    that new Notification.
    """
    registration = notification.registration
    builder = _RESENDABLE_EMAIL_BUILDERS.get(notification.notification_type)

    if registration and builder:
        subject, text, html = builder(registration)
        return send_email(
            to=to,
            subject=subject,
            text_body=text,
            html_body=html,
            registration=registration,
            notification_type=notification.notification_type,
        )

    return send_email(
        to=to,
        subject=notification.subject or "(no subject)",
        text_body=notification.body,
        registration=registration,
        notification_type=notification.notification_type,
    )
