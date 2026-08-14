from decimal import Decimal
from rest_framework import serializers

from .models import PaymentAccount, PaymentProvider


class InitiatePaymentSerializer(
    serializers.Serializer
):

    payment_method = serializers.ChoiceField(
        choices=[
            "MTN_MONEY",
            "AIRTEL_MONEY",
            "ZAMTEL_KWACHA",
            "CARD",
            "BANK_TRANSFER",
        ]
    )

    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    payer_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
    )

    transfer_reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )

    # Card only — Lipila's hosted checkout needs a billing address for
    # fraud scoring, even though we never see the card number itself.
    city = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )

    address = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )

    zip_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
    )

    country = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2,
        default="ZM",
    )

    def validate(self, attrs):

        method = attrs[
            "payment_method"
        ]

        if (
            method not in ("CARD", "BANK_TRANSFER")
            and not attrs.get("phone_number")
        ):
            raise serializers.ValidationError(
                {
                    "phone_number": (
                        "Phone number is required "
                        "for mobile money payments."
                    )
                }
            )

        if (
            method == "BANK_TRANSFER"
            and not attrs.get("payer_name")
        ):
            raise serializers.ValidationError(
                {
                    "payer_name": (
                        "Please enter the name the "
                        "transfer will be made from."
                    )
                }
            )

        if method == "CARD":

            missing = {
                field: "This field is required for card payments."
                for field in ("city", "address", "zip_code")
                if not attrs.get(field)
            }

            if missing:
                raise serializers.ValidationError(missing)

        return attrs


# ---------------------------------------------------------------------------
# Admin-facing serializers
# ---------------------------------------------------------------------------

from .models import (
    Payment,
    PaymentAccount,
    Transaction,
    Wallet,
    Withdrawal,
)


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = (
            "id",
            "wallet",
            "transaction_type",
            "direction",
            "status",
            "amount",
            "currency",
            "reference",
            "provider_reference",
            "description",
            "created_at",
            "posted_at",
        )


class PaymentSerializer(serializers.ModelSerializer):

    registration_number = serializers.CharField(
        source="registration.registration_number",
        read_only=True,
    )

    participant_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "registration",
            "registration_number",
            "participant_name",
            "reference",
            "provider_reference",
            "amount",
            "currency",
            "status",
            "payment_method",
            "paid_at",
            "created_at",
        )

    def get_participant_name(self, obj):
        p = obj.registration.participant
        return f"{p.first_name} {p.last_name}".strip()


class WalletSerializer(serializers.ModelSerializer):

    balance = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    pending_balance = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Wallet
        fields = (
            "id",
            "event",
            "currency",
            "balance",
            "pending_balance",
        )


class WithdrawalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Withdrawal
        fields = (
            "id",
            "wallet",
            "reference",
            "provider_reference",
            "destination",
            "destination_account",
            "recipient_name",
            "amount",
            "currency",
            "status",
            "narration",
            "requested_at",
            "completed_at",
        )
        read_only_fields = (
            "reference",
            "provider_reference",
            "status",
            "requested_at",
            "completed_at",
        )


class WithdrawalRequestSerializer(serializers.Serializer):
    """Input serializer for POST /admin/wallet/withdraw/"""

    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    destination = serializers.ChoiceField(
        choices=Withdrawal.Destination.choices
    )
    destination_account = serializers.CharField(max_length=150)
    recipient_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    narration = serializers.CharField(max_length=255, required=False, allow_blank=True)


class SendMoneySerializer(serializers.Serializer):
    """
    Input serializer for POST /admin/wallet/send-money/ — an ad-hoc
    disbursement to any mobile money number (not necessarily a
    withdrawal to the organiser; e.g. a manual payout or correction).
    Implemented as a Withdrawal record under the hood so it shows up in
    the same ledger/audit trail.
    """

    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    account_number = serializers.CharField(max_length=150)
    recipient_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    narration = serializers.CharField(max_length=255, required=False, allow_blank=True)


class RefundRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal('0.01'), required=False
    )


class PaymentProviderSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentProvider
        fields = (
            "id",
            "name",
            "code",
            "provider_type",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PaymentAccountSerializer(serializers.ModelSerializer):

    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    provider_name = serializers.CharField(
        source="provider.name", read_only=True
    )

    class Meta:
        model = PaymentAccount
        fields = (
            "id",
            "organization",
            "organization_name",
            "provider",
            "provider_name",
            "account_type",
            "name",
            "provider_account_id",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization_name",
            "provider_name",
            "created_at",
            "updated_at",
        )