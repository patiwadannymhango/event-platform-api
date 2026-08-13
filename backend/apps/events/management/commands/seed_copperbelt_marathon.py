"""
Seeds everything the Copperbelt Marathon 2026 registration site needs:
an Organization, a Lipila PaymentProvider/PaymentAccount, a Wallet, the
Event itself, its RegistrationForm + fields (matching the public site's
form), and the 8 race categories with their fees.

Run once:  python manage.py seed_copperbelt_marathon
Safe to re-run — it updates in place rather than duplicating.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.organizations.models import Organization
from apps.payments.models import PaymentAccount, PaymentProvider, Wallet
from apps.events.models import Event
from apps.registrations.models import (
    RegistrationCategory,
    RegistrationField,
    RegistrationForm,
)


CATEGORIES = [
    {"code": "full-marathon", "name": "Full Marathon", "distance": "42.195 KM", "price": 2},
    {"code": "half-marathon", "name": "Half Marathon", "distance": "21.1 KM", "price": 2},
    {"code": "10k", "name": "10K", "distance": "10 KM", "price": 2},
    {"code": "5k-fun-run", "name": "Fun Run & Walk", "distance": "5 KM", "price": 2},
    {"code": "mining-challenge", "name": "Mining Challenge", "distance": "", "price": 2},
    {"code": "differently-abled", "name": "Differently Abled Challenge", "distance": "", "price": 2},
    {"code": "schools-youth", "name": "Schools & Youth Challenge", "distance": "5 KM", "price": 2},
    {"code": "veterans", "name": "Veterans Challenge", "distance": "10 KM", "price": 2},
]

FIELDS = [
    {"key": "gender", "label": "Gender", "type": RegistrationField.FieldType.SELECT,
     "options": [{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}]},
    {"key": "age_range", "label": "Age range", "type": RegistrationField.FieldType.SELECT,
     "options": [{"value": v, "label": v} for v in
                 ["Under 18", "18-29", "30-39", "40-49", "50-59", "60+"]]},
    {"key": "country", "label": "Country", "type": RegistrationField.FieldType.TEXT, "options": []},
    {"key": "tshirt_size", "label": "T-shirt size", "type": RegistrationField.FieldType.SELECT,
     "options": [{"value": v, "label": v} for v in
                 ["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]]},
    {"key": "attendance_type", "label": "Attendance type", "type": RegistrationField.FieldType.RADIO,
     "options": [{"value": "in-person", "label": "In-person"}, {"value": "virtual", "label": "Virtual"}]},
    {"key": "club_or_institution", "label": "Club / institution", "type": RegistrationField.FieldType.TEXT, "options": []},
    {"key": "emergency_contact_name", "label": "Emergency contact name", "type": RegistrationField.FieldType.TEXT, "options": []},
    {"key": "emergency_contact_phone", "label": "Emergency contact phone", "type": RegistrationField.FieldType.PHONE, "options": []},
    {"key": "medical_notes", "label": "Medical notes", "type": RegistrationField.FieldType.TEXTAREA, "options": []},
]


class Command(BaseCommand):
    help = "Seed the Copperbelt Marathon 2026 event, categories and form."

    def handle(self, *args, **options):

        organization, _ = Organization.objects.get_or_create(
            slug="copperbelt-marathon",
            defaults={
                "name": "Copperbelt Marathon",
                "email": "info@copperbeltmarathon2026.org",
            },
        )

        provider, _ = PaymentProvider.objects.get_or_create(
            code="lipila",
            defaults={
                "name": "Lipila",
                "provider_type": PaymentProvider.ProviderType.LIPILA,
            },
        )

        payment_account, _ = PaymentAccount.objects.get_or_create(
            organization=organization,
            provider=provider,
            provider_account_id="",
            defaults={
                "name": "Copperbelt Marathon Lipila Account",
                "account_type": PaymentAccount.AccountType.MERCHANT,
                "currency": "ZMW",
            },
        )

        event, created = Event.objects.get_or_create(
            organization=organization,
            slug="copperbelt-marathon-2026",
            defaults={
                "name": "Copperbelt Marathon 2026",
                "description": "Road running festival through Kitwe, Zambia.",
                "start_date": timezone.datetime(2026, 10, 10, 6, 0, tzinfo=timezone.get_current_timezone()),
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

        for cat in CATEGORIES:
            RegistrationCategory.objects.update_or_create(
                event=event,
                code=cat["code"],
                defaults={
                    "name": cat["name"],
                    "description": cat["distance"],
                    "price": cat["price"] if cat["price"] is not None else 0,
                    "currency": "ZMW",
                },
            )

        form, _ = RegistrationForm.objects.get_or_create(
            event=event,
            defaults={"name": "Copperbelt Marathon 2026 Registration"},
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
                    "is_required": field["key"] in {"attendance_type"},
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Event ID: {event.id}"))
        self.stdout.write(
            self.style.WARNING(
                f"Set CURRENT_EVENT_ID={event.id} in your .env, and "
                f"VITE_EVENT_ID={event.id} in the frontend's .env."
            )
        )
