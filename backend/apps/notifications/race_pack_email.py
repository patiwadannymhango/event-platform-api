"""
Builds the "Race Pack Collection Details" email — (subject, text, html)
for one recipient.

The logo is embedded as a CID attachment (see LOGO_STATIC_PATH /
apps/notifications/email.py's inline_images) rather than linked as a
hosted URL — a hosted-URL version of this email had its logo silently
fail to show in Outlook, most likely the oversized original file
(921KB at 1224x1285 for a 100x100 slot) combined with Outlook's
default of not auto-loading remote images. An embedded image is part
of the downloaded message itself, so it renders regardless of either.
An even earlier base64 data: URI version had the same failure for a
different reason (Outlook doesn't render data: URIs or CSS gradients
at all) — CID embedding is the one approach that sidesteps both.
"""

from django.conf import settings
from django.contrib.staticfiles.finders import find as find_static
from django.template.loader import render_to_string

SUBJECT = "Copperbelt Marathon 2026 — Race Pack Collection Details"

LOGO_CONTENT_ID = "race_pack_logo"

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
    """
    Returns (subject, text_body, html_body, inline_images) for one
    recipient — inline_images is ready to pass straight through to
    send_email()'s inline_images= kwarg.
    """
    text = _TEXT_TEMPLATE.format(
        first_name=first_name,
        reference=reference,
        contact_email=settings.DEFAULT_FROM_EMAIL,
        contact_phone_line=f" / {settings.EVENT_CONTACT_PHONE}" if settings.EVENT_CONTACT_PHONE else "",
    )

    html = render_to_string(
        "notifications/emails/race_pack_collection.html",
        {
            "first_name": first_name,
            "reference": reference,
            "event_name": "Copperbelt Marathon 2026",
            "contact_email": settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    logo_path = find_static("notifications/email/logo.png")
    inline_images = [(LOGO_CONTENT_ID, logo_path)] if logo_path else []

    return SUBJECT, text, html, inline_images
