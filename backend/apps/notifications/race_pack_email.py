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

# Both days, shown to everyone by default. The "purple group" (confirmed
# since the 5 October print-dump cutoff — see PURPLE_SINCE_CUTOFF in the
# admin's Registrations.tsx) gets a Friday-only variant instead, to spread
# collection across the two days rather than everyone showing up at once.
COLLECTION_HEADING_DEFAULT = "Corporate and Individual Collection"
COLLECTION_DAYS_BOTH = [
    {"label": "8th October (Thursday)", "time": "09:00 – 17:00"},
    {"label": "9th October (Friday)", "time": "09:00 – 17:00"},
]
COLLECTION_DAYS_FRIDAY_ONLY = [
    {"label": "9th October (Friday)", "time": "09:00 – 17:00"},
]

# Thursday reserved for corporate groups only, Friday for everyone else —
# a per-day note tags which audience each row is for, rather than lumping
# both under one generic heading.
COLLECTION_HEADING_SPLIT = "Collection Schedule"
COLLECTION_DAYS_SPLIT_BY_AUDIENCE = [
    {"label": "8th October (Thursday)", "time": "09:00 – 17:00", "note": "Corporate Collection Only"},
    {"label": "9th October (Friday)", "time": "09:00 – 17:00", "note": "Individual Collection"},
]

_TEXT_TEMPLATE = """Dear {first_name},

Please see the 10th October - Copperbelt Marathon 2026 Race Pack Collection details below:

Virtual Participants: Race Packs Will Be Sent.

{collection_heading}:
{collection_days_text}

Venue: ECL Mall, Kitwe - Marathon Registration Desk

Please come with your Marathon Registration Number ({reference}) for collection.
NO BIB, NO MEDAL.

Questions? {contact_email}{contact_phone_line}

See you on race day!"""


def build_race_pack_email(*, first_name, reference, collection_days=None, collection_heading=None):
    """
    Returns (subject, text_body, html_body, inline_images) for one
    recipient — inline_images is ready to pass straight through to
    send_email()'s inline_images= kwarg.

    collection_days: list of {"label", "time", "note"?} dicts to show, in
    order ("note" is an optional small audience tag above the date, e.g.
    "Corporate Collection Only"). Defaults to both Thursday and Friday
    with no notes. Pass COLLECTION_DAYS_FRIDAY_ONLY for the purple group,
    or COLLECTION_DAYS_SPLIT_BY_AUDIENCE for the Thursday-is-corporate-only
    variant (pair with COLLECTION_HEADING_SPLIT).
    collection_heading: section heading above the day(s). Defaults to
    COLLECTION_HEADING_DEFAULT.
    """
    if collection_days is None:
        collection_days = COLLECTION_DAYS_BOTH
    if collection_heading is None:
        collection_heading = COLLECTION_HEADING_DEFAULT

    collection_days_text = "\n".join(
        f"{day['note'] + ' — ' if day.get('note') else ''}{day['label']}: {day['time'].replace(chr(0x2013), '-')}hrs"
        for day in collection_days
    )

    text = _TEXT_TEMPLATE.format(
        first_name=first_name,
        reference=reference,
        collection_heading=collection_heading,
        collection_days_text=collection_days_text,
        contact_email=settings.DEFAULT_FROM_EMAIL,
        contact_phone_line=f" / {settings.EVENT_CONTACT_PHONE}" if settings.EVENT_CONTACT_PHONE else "",
    )

    html = render_to_string(
        "notifications/emails/race_pack_collection.html",
        {
            "first_name": first_name,
            "reference": reference,
            "event_name": "Copperbelt Marathon 2026",
            "collection_heading": collection_heading,
            "collection_days": collection_days,
            "contact_email": settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    logo_path = find_static("notifications/email/logo.png")
    inline_images = [(LOGO_CONTENT_ID, logo_path)] if logo_path else []

    return SUBJECT, text, html, inline_images
