from django.utils import timezone
from rest_framework import serializers, status

from apps.participants.models import Participant

from .models import (
    Registration,
    RegistrationCategory,
    RegistrationField,
    RegistrationForm,
)


class RegistrationFieldSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = RegistrationField

        fields = (
            "id",
            "name",
            "label",
            "field_type",
            "key",
            "help_text",
            "placeholder",
            "is_required",
            "display_order",
            "validation_rules",
            "options",
        )


class RegistrationCategorySerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = RegistrationCategory

        fields = (
            "id",
            "name",
            "code",
            "description",
            "price",
            "currency",
            "capacity",
            "registration_start",
            "registration_end",
        )


class RegistrationFormSerializer(
    serializers.ModelSerializer
):

    fields = RegistrationFieldSerializer(
        many=True,
        read_only=True,
    )

    categories = serializers.SerializerMethodField()

    class Meta:
        model = RegistrationForm

        fields = (
            "id",
            "event",
            "name",
            "description",
            "fields",
            "categories",
        )

    def get_categories(self, obj):

        categories = (
            obj.event
            .registration_categories
            .filter(is_active=True)
        )

        return RegistrationCategorySerializer(
            categories,
            many=True,
        ).data
    

class PublicRegistrationSerializer(
    serializers.Serializer
):

    category_id = serializers.UUIDField()

    participant = serializers.DictField()

    form_data = serializers.DictField(
        required=False,
        default=dict,
    )

    reserve = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "If true, hold the spot without requiring payment now "
            "(status RESERVED); otherwise the registration is created "
            "PENDING_PAYMENT and expects a payment to be initiated next."
        ),
    )

    def validate(self, attrs):

        event = self.context["event"]

        category_id = attrs["category_id"]


        if not event.is_active:
            raise serializers.ValidationError(
                "This event is not active."
            )

        if event.status != "PUBLISHED":
            raise serializers.ValidationError(
                "Registration is not currently open for this event."
            )

        try:
            category = (
                RegistrationCategory.objects.get(
                    id=category_id,
                    event=event,
                    is_active=True,
                )
            )
        except RegistrationCategory.DoesNotExist:

            raise serializers.ValidationError(
                {
                    "category_id": (
                        "Invalid registration category."
                    )
                }
            )

        now = timezone.now()

        if (
            category.registration_start
            and now < category.registration_start
        ):
            raise serializers.ValidationError(
                {
                    "category_id": (
                        "Registration for this category "
                        "has not started."
                    )
                }
            )

        if (
            category.registration_end
            and now > category.registration_end
        ):
            raise serializers.ValidationError(
                {
                    "category_id": (
                        "Registration for this category "
                        "has closed."
                    )
                }
            )

        if category.capacity is not None:

            current_count = (
                Registration.objects.filter(
                    category=category,
                    status__in=[
                        Registration.Status.PENDING_PAYMENT,
                        Registration.Status.PAYMENT_PROCESSING,
                        Registration.Status.CONFIRMED,
                    ],
                ).count()
            )

            if current_count >= category.capacity:

                raise serializers.ValidationError(
                    {
                        "category_id": (
                            "This registration category "
                            "has reached capacity."
                        )
                    }
                )

        attrs["category"] = category

        return attrs

    
    def validate_form_data(self, value):

        event = self.context["event"]

        try:
            form = event.registration_form

        except RegistrationForm.DoesNotExist:

            raise serializers.ValidationError(
                "This event does not have a registration form."
            )

        fields = form.fields.filter(
            is_active=True
        )

        submitted_keys = set(value.keys())

        errors = {}

        for field in fields:

            field_value = value.get(field.key)

            # Required field validation
            if (
                field.is_required
                and (
                    field_value is None
                    or field_value == ""
                )
            ):
                errors[field.key] = (
                    f"{field.label} is required."
                )

            # Field type validation
            try:
                self.validate_field_value(
                    field,
                    field_value,
                )
            except serializers.ValidationError as exc:
                errors[field.key] = str(exc.detail[0])

        # Check for fields that don't exist
        allowed_keys = {
            field.key
            for field in fields
        }

        unknown_fields = (
            submitted_keys - allowed_keys
        )

        if unknown_fields:

            errors["form_data"] = (
                "Unknown fields submitted: "
                + ", ".join(
                    sorted(unknown_fields)
                )
            )

        if errors:
            raise serializers.ValidationError(
                errors
            )

        return value

    def validate_field_value(
        self,
        field,
        value,
    ):

        if value in (
            None,
            "",
        ):
            return

        if field.field_type == (
            RegistrationField.FieldType.EMAIL
        ):

            from django.core.validators import (
                validate_email,
            )
            from django.core.exceptions import (
                ValidationError,
            )

            try:
                validate_email(value)

            except ValidationError:

                raise serializers.ValidationError(
                    f"{field.label} must be a valid email."
                )

        if field.field_type == (
            RegistrationField.FieldType.NUMBER
        ):

            try:
                float(value)

            except (
                TypeError,
                ValueError,
            ):

                raise serializers.ValidationError(
                    f"{field.label} must be a number."
                )

        if field.field_type in (
            RegistrationField.FieldType.SELECT,
            RegistrationField.FieldType.RADIO,
        ):

            allowed_values = {
                option["value"]
                for option in field.options
            }

            if value not in allowed_values:

                raise serializers.ValidationError(
                    f"Invalid value for {field.label}."
                )



# ---------------------------------------------------------------------------
# Admin-facing serializers
# ---------------------------------------------------------------------------

from apps.participants.models import Participant as ParticipantModel


class AdminParticipantSerializer(serializers.ModelSerializer):

    class Meta:
        model = ParticipantModel
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
        )


class AdminRegistrationSerializer(serializers.ModelSerializer):
    """
    Full read serializer for the admin registrations table — flattens
    participant fields alongside the registration so the frontend doesn't
    need a second request per row.
    """

    participant = AdminParticipantSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    event_name = serializers.CharField(source="event.name", read_only=True)
    payment_reference = serializers.SerializerMethodField()
    created_via_display = serializers.CharField(source="get_created_via_display", read_only=True)
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = (
            "id",
            "registration_number",
            "status",
            "amount",
            "currency",
            "participant",
            "category",
            "category_name",
            "event",
            "event_name",
            "form_data",
            "payment_reference",
            "created_via",
            "created_via_display",
            "created_by",
            "registered_at",
            "updated_at",
        )

    def get_created_by(self, obj):
        # Only ever set for created_via=ADMIN — a public self-registration
        # has no logged-in admin account behind it. AdminRegistrationListView
        # select_relates this, so accessing it here doesn't add a query per
        # row; the single-object views (detail/create/edit) hit it live,
        # which is fine there since they only ever serialize one row.
        if not obj.created_by_id:
            return None
        return {
            "full_name": obj.created_by.full_name,
            "email": obj.created_by.email,
        }

    def get_payment_reference(self, obj):
        # The gateway (Lipila)'s own transaction reference for this
        # registration's payment — prefers a successful one (the real
        # transaction that actually confirmed it); falls back to the most
        # recent attempt so a pending/failed registration still shows
        # something useful for looking it up in Lipila's dashboard.
        # AdminRegistrationListView prefetches this as `_all_payments` to
        # avoid a query per row; other views (detail/create/edit, which
        # only ever serialize one registration) fall back to a live query.
        payments = getattr(obj, "_all_payments", None)
        if payments is None:
            payments = list(obj.payments.order_by("-created_at"))

        payment = next((p for p in payments if p.status == "SUCCESS"), None)
        if payment is None and payments:
            payment = payments[0]

        return payment.provider_reference if payment else ""


class AdminRegistrationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Registration.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True)


class AdminManualRegistrationSerializer(serializers.Serializer):
    """
    For the admin's "register a participant" form — same shape as the
    public serializer but lets the admin pick the initial status directly
    (e.g. mark it CONFIRMED immediately for a cash payment taken in
    person) instead of always starting PENDING_PAYMENT/RESERVED.
    """

    category_id = serializers.UUIDField()
    participant = serializers.DictField()
    form_data = serializers.DictField(required=False, default=dict)
    status = serializers.ChoiceField(
        choices=Registration.Status.choices,
        default=Registration.Status.CONFIRMED,
    )

    def validate_category_id(self, value):
        event = self.context["event"]
        try:
            return RegistrationCategory.objects.get(
                id=value, event=event, is_active=True
            )
        except RegistrationCategory.DoesNotExist:
            raise serializers.ValidationError("Invalid registration category.")
