"""
Seeds the Copperbelt Marathon 2026 Vendor & Exhibitor Registration event —
a separate Event from the runner event (a RegistrationForm is one-per-
event, and vendor fields have nothing to do with runner fields), reusing
the same Organization and Lipila PaymentAccount.

Run once, manually:  python manage.py seed_vendor_registration
Deliberately NOT wired into docker-entrypoint.sh — see
seed_copperbelt_marathon.py's history for why an auto-rerunning seed
command is dangerous if it ever touches already-live operational data
(price, in that incident). Safe to re-run regardless: categories keep
their price once created; only name/label fields refresh.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.organizations.models import Organization
from apps.payments.models import PaymentAccount, PaymentProvider, Wallet
from apps.events.models import Event
from apps.registrations.models import (
    RegistrationCategory,
    RegistrationField,
    RegistrationForm,
)


CATEGORIES = [
    {"code": "sme", "name": "SME", "price": 500},
    {"code": "vendor", "name": "Vendor", "price": 1000},
    {"code": "corporate", "name": "Corporate", "price": 10000},
    {"code": "official-sponsor", "name": "Official Sponsor", "price": 0},
]

FIELDS = [
    {"key": "business_name", "label": "Business / Company Name",
     "type": RegistrationField.FieldType.TEXT, "options": []},
    {"key": "business_location", "label": "Business Location",
     "type": RegistrationField.FieldType.TEXT, "options": []},
    {"key": "products_services", "label": "Products / Services",
     "type": RegistrationField.FieldType.TEXTAREA, "options": []},
    {"key": "requirement", "label": "Exhibition / Activation Requirement",
     "type": RegistrationField.FieldType.SELECT,
     "options": [{"value": v, "label": v} for v in [
         "Exhibition Space",
         "Vendor Stall",
         "Food & Beverage Stall",
         "Corporate Activation",
         "Branding / Promotional Space",
         "Other",
     ]]},
]


class Command(BaseCommand):
    help = "Seed the Copperbelt Marathon 2026 Vendor & Exhibitor Registration event."

    def handle(self, *args, **options):

        organization = Organization.objects.get(slug="copperbelt-marathon")
        provider = PaymentProvider.objects.get(code="lipila")
        payment_account = PaymentAccount.objects.get(
            organization=organization, provider=provider
        )

        # Deliberately not "copperbelt-marathon-2026-vendors" — that
        # truncates to the same 6-character registration_number prefix
        # ("COPPER") as the runner event and collides with it the moment
        # anyone registers. See generate_registration_number()'s docstring
        # in services.py for the full story.
        event, created = Event.objects.get_or_create(
            organization=organization,
            slug="cbm-vendors-2026",
            defaults={
                "name": "Copperbelt Marathon 2026 — Vendor & Exhibitor Registration",
                "description": (
                    "Vendor, exhibitor and sponsor registration for "
                    "Copperbelt Marathon 2026."
                ),
                "start_date": timezone.datetime(
                    2026, 10, 10, 6, 0, tzinfo=timezone.get_current_timezone()
                ),
                "location": "ECL Mall, Kitwe",
                "status": Event.Status.PUBLISHED,
                "payment_account": payment_account,
            },
        )

        if not event.payment_account_id:
            event.payment_account = payment_account
            event.status = Event.Status.PUBLISHED
            event.save(update_fields=["payment_account", "status"])

        Wallet.objects.get_or_create(event=event, defaults={"currency": "ZMW"})

        # Price is only ever set on first creation — never touched again
        # on a later run of this command.
        for cat in CATEGORIES:
            category, cat_created = RegistrationCategory.objects.get_or_create(
                event=event,
                code=cat["code"],
                defaults={
                    "name": cat["name"],
                    "description": "",
                    "price": cat["price"],
                    "currency": "ZMW",
                },
            )
            if not cat_created:
                category.name = cat["name"]
                category.save(update_fields=["name"])

        form, _ = RegistrationForm.objects.get_or_create(
            event=event,
            defaults={"name": "Vendor & Exhibitor Registration"},
        )

        for order, field in enumerate(FIELDS):
            RegistrationField.objects.update_or_create(
                form=form,
                key=field["key"],
                defaults={
                    "name": field["key"],
                    "label": field["label"],
                    "field_type": field["type"],
                    "display_order": order,
                    "options": field["options"],
                    "is_required": True,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Event ID: {event.id}"))
        self.stdout.write(
            self.style.WARNING(
                f"Set VITE_VENDOR_EVENT_ID={event.id} in the site's .env."
            )
        )
