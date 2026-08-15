from django.db import models

from apps.common.models import UUIDModel


class RegistrationForm(UUIDModel):

    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="registration_form",
    )

    name = models.CharField(
        max_length=200,
        default="Registration Form",
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.event.name} Registration Form"
    


class RegistrationField(UUIDModel):

    class FieldType(models.TextChoices):

        TEXT = "TEXT", "Text"

        TEXTAREA = "TEXTAREA", "Long Text"

        EMAIL = "EMAIL", "Email"

        PHONE = "PHONE", "Phone"

        NUMBER = "NUMBER", "Number"

        DATE = "DATE", "Date"

        SELECT = "SELECT", "Select"

        RADIO = "RADIO", "Radio"

        CHECKBOX = "CHECKBOX", "Checkbox"

        FILE = "FILE", "File"

    form = models.ForeignKey(
        RegistrationForm,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    name = models.CharField(
        max_length=150,
    )

    label = models.CharField(
        max_length=255,
    )

    field_type = models.CharField(
        max_length=30,
        choices=FieldType.choices,
    )

    key = models.SlugField(
        max_length=100,
    )

    help_text = models.CharField(
        max_length=500,
        blank=True,
    )

    placeholder = models.CharField(
        max_length=255,
        blank=True,
    )

    is_required = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    validation_rules = models.JSONField(
        default=dict,
        blank=True,
    )

    options = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "form",
                    "key",
                ],
                name="unique_registration_field_key",
            )
        ]

    def __str__(self):
        return f"{self.form} - {self.label}"


    
class RegistrationCategory(UUIDModel):

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="registration_categories",
    )

    name = models.CharField(
        max_length=150,
    )

    code = models.SlugField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="ZMW",
    )

    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    registration_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    registration_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event",
                    "code",
                ],
                name="unique_event_registration_category",
            )
        ]

    def __str__(self):
        return f"{self.event.name} - {self.name}"
    


class Registration(UUIDModel):

    class Status(models.TextChoices):

        DRAFT = "DRAFT", "Draft"

        PENDING_PAYMENT = (
            "PENDING_PAYMENT_TEs",
            "Pending Payment",
        )

        PAYMENT_PROCESSING = (
            "PAYMENT_PROCESSING",
            "Payment Processing",
        )

        RESERVED = (
            "RESERVED",
            "Reserved (Pay Later)",
        )

        CONFIRMED = (
            "CONFIRMED",
            "Confirmed",
        )

        CANCELLED = (
            "CANCELLED",
            "Cancelled",
        )

        EXPIRED = (
            "EXPIRED",
            "Expired",
        )

        REFUNDED = (
            "REFUNDED",
            "Refunded",
        )

    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.PROTECT,
        related_name="registrations",
    )

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.PROTECT,
        related_name="registrations",
    )

    category = models.ForeignKey(
        RegistrationCategory,
        on_delete=models.PROTECT,
        related_name="registrations",
    )

    registration_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="ZMW",
    )

    form_data = models.JSONField(
        default=dict,
        blank=True,
    )

    registered_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-registered_at",
        ]

    def __str__(self):
        return self.registration_number