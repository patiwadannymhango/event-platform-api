"""
Builds the "Race Pack Collection Details" email — (subject, text, html)
for one recipient.

Follows the same pattern as _build_payment_confirmed_email in
services.py: a Django template rendered via render_to_string, with the
logo served from a real hosted URL (settings.PUBLIC_BASE_URL + the
static file already used by the confirmation email) rather than a
base64 data: URI. Outlook's desktop client (and some others) simply
doesn't render data: URI images or CSS gradients — an earlier base64
version of this email had its header silently fail to render for
exactly that reason.
"""

from django.conf import settings
from django.template.loader import render_to_string

SUBJECT = "Copperbelt Marathon 2026 — Race Pack Collection Details"

_TEXT_TEMPLATE = """Dear {first_name},

Please see the 10th October - Copperbelt Marathon 2026 Race Pack Collection details below:

Virtual Participants: Race Packs Will Be Sent.

Corporate and Individual Collection:
8th October (Thursday): 09:00hrs-17:00hrs
9th October (Friday): 09:00hrs-17:00hrs

Venue: ECL Mall, Kitwe - Marathon Registration Desk

Please come with your Marathon Registration Number ({reference}) for collection.
NO BIB, NO MEDAL.

Questions? {contact_email}{contact_phone_line}

See you on race day!"""


def build_race_pack_email(*, first_name, reference):
    """Returns (subject, text_body, html_body) for one recipient."""
    text = _TEXT_TEMPLATE.format(
        first_name=first_name,
        reference=reference,
        contact_email=settings.DEFAULT_FROM_EMAIL,
        contact_phone_line=f" / {settings.EVENT_CONTACT_PHONE}" if settings.EVENT_CONTACT_PHONE else "",
    )

    logo_url = (
        f"{settings.PUBLIC_BASE_URL}/static/notifications/email/logo.png"
        if settings.PUBLIC_BASE_URL
        else ""
    )

    html = render_to_string(
        "notifications/emails/race_pack_collection.html",
        {
            "first_name": first_name,
            "reference": reference,
            "event_name": "Copperbelt Marathon 2026",
            "logo_url": logo_url,
            "contact_email": settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    return SUBJECT, text, html
