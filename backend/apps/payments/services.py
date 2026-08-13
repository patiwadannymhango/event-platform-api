import uuid

from django.db import transaction

from .models import Payment


@transaction.atomic
def create_payment(
    *,
    registration,
    payment_method,
):

    payment_account = (
        registration.event.payment_account
    )

    if not payment_account:
        raise ValueError(
            "This event has no payment account configured."
        )

    provider = payment_account.provider

    reference = (
        f"PAY-{uuid.uuid4().hex[:16].upper()}"
    )

    payment = Payment.objects.create(
        registration=registration,
        provider=provider,
        payment_account=payment_account,
        wallet=registration.event.wallet,
        reference=reference,
        amount=registration.amount,
        currency=registration.currency,
        payment_method=payment_method,
        status=Payment.Status.PENDING,
    )

    return payment

def initiate_mobile_payment(
    *,
    payment,
    phone_number,
    callback_url,
):

    provider = payment.provider

    if provider.provider_type != "LIPILA":

        raise ValueError(
            "This payment provider is not Lipila."
        )

    from .providers.lipila.services import (
        LipilaProvider,
    )

    lipila = LipilaProvider()

    response = (
        lipila.create_mobile_collection(
            reference_id=payment.reference,
            amount=payment.amount,
            account_number=phone_number,
            currency=payment.currency,
            narration=(
                f"Event registration "
                f"{payment.registration.registration_number}"
            ),
            reference_data=(
                payment.registration.registration_number
            ),
            callback_url=callback_url,
        )
    )

    payment.provider_response = response

    payment.provider_reference = (
        response.get("referenceId", "")
    )

    payment.status = (
        Payment.Status.PROCESSING
    )

    payment.save(
        update_fields=[
            "provider_response",
            "provider_reference",
            "status",
            "updated_at",
        ]
    )

    return payment


def initiate_card_payment(
    *,
    payment,
    participant,
    city,
    address,
    zip_code,
    country,
    callback_url,
    back_url,
):
    """
    Card payments are a hosted-checkout redirect (Visa/Mastercard/Amex
    via Lipila's PCI-compliant page) — this never handles a card number.
    Returns (payment, redirect_url); the caller sends the browser to
    redirect_url and the outcome arrives later via the same webhook that
    handles mobile money.
    """

    provider = payment.provider

    if provider.provider_type != "LIPILA":

        raise ValueError(
            "This payment provider is not Lipila."
        )

    from .providers.lipila.services import (
        LipilaProvider,
    )

    lipila = LipilaProvider()

    response = lipila.create_card_collection(
        reference_id=payment.reference,
        amount=payment.amount,
        currency=payment.currency,
        first_name=participant.first_name,
        last_name=participant.last_name,
        phone_number=participant.phone,
        email=participant.email,
        city=city,
        address=address,
        zip_code=zip_code,
        country=country,
        narration=(
            f"Event registration "
            f"{payment.registration.registration_number}"
        ),
        reference_data=(
            payment.registration.registration_number
        ),
        back_url=back_url,
        callback_url=callback_url,
    )

    payment.provider_response = response

    payment.provider_reference = (
        response.get("referenceId", "")
    )

    payment.status = (
        Payment.Status.PROCESSING
    )

    payment.save(
        update_fields=[
            "provider_response",
            "provider_reference",
            "status",
            "updated_at",
        ]
    )

    redirect_url = response.get(
        "cardRedirectionUrl", ""
    )

    return payment, redirect_url


def get_live_balance(payment_account):
    """
    Fetch the live float balance from Lipila for a payment account.
    Falls back to raising — callers should catch and fall back to the
    ledger balance (Wallet.balance) if the live call fails, so the admin
    dashboard never just breaks because Lipila is briefly unreachable.
    """

    provider = payment_account.provider

    if provider.provider_type != "LIPILA":
        raise ValueError("This payment provider is not Lipila.")

    from .providers.lipila.services import LipilaProvider

    lipila = LipilaProvider()

    return lipila.get_balance()


@transaction.atomic
def process_refund(*, payment, amount=None, requested_by=None):
    """
    Full refund flow: calls Lipila to send the money back, then posts the
    ledger entry and flips the payment/registration status. If the
    Lipila call fails, nothing is posted to the ledger — the exception
    propagates so the admin sees the failure instead of a silently wrong
    balance.
    """

    from .ledger import post_refund
    from .providers.lipila.services import LipilaProvider
    from apps.registrations.models import Registration

    refund_amount = amount or payment.amount
    participant = payment.registration.participant

    reference = f"RF-{uuid.uuid4().hex[:16].upper()}"

    lipila = LipilaProvider()

    response = lipila.create_disbursement(
        reference_id=reference,
        amount=refund_amount,
        account_number=participant.phone,
        currency=payment.currency,
        full_name=f"{participant.first_name} {participant.last_name}".strip(),
        phone_number=participant.phone,
        email=participant.email,
        narration=f"Refund for {payment.registration.registration_number}",
    )

    payment, financial_transaction = post_refund(
        payment=payment,
        amount=refund_amount,
        reference=reference,
    )

    registration = payment.registration
    registration.status = Registration.Status.REFUNDED
    registration.save(update_fields=["status", "updated_at"])

    return payment, financial_transaction, response


@transaction.atomic
def request_withdrawal(
    *,
    wallet,
    amount,
    destination,
    destination_account,
    recipient_name="",
    narration="",
    requested_by=None,
    send_via_lipila=True,
):
    """
    Create a Withdrawal request and, for mobile-money withdrawals, send
    the money out via Lipila immediately. Bank/cash withdrawals are
    created in REQUESTED status for manual processing outside the
    system (mark them COMPLETED once the transfer/cash handout is done).
    """

    from .models import Withdrawal
    from .ledger import post_withdrawal

    reference = f"WD-{uuid.uuid4().hex[:16].upper()}"

    withdrawal = Withdrawal.objects.create(
        wallet=wallet,
        reference=reference,
        destination=destination,
        destination_account=destination_account,
        recipient_name=recipient_name,
        amount=amount,
        currency=wallet.currency,
        narration=narration,
        requested_by=requested_by,
        status=Withdrawal.Status.REQUESTED,
    )

    if destination == Withdrawal.Destination.MOBILE_MONEY and send_via_lipila:

        from .providers.lipila.services import LipilaProvider

        lipila = LipilaProvider()

        response = lipila.create_disbursement(
            reference_id=reference,
            amount=amount,
            account_number=destination_account,
            currency=wallet.currency,
            full_name=recipient_name,
            phone_number=destination_account,
            narration=narration or f"Withdrawal {reference}",
        )

        withdrawal.provider_response = response
        withdrawal.provider_reference = response.get("referenceId", "")
        withdrawal.status = Withdrawal.Status.COMPLETED

        from django.utils import timezone
        withdrawal.completed_at = timezone.now()

        withdrawal.save(
            update_fields=[
                "provider_response",
                "provider_reference",
                "status",
                "completed_at",
                "updated_at",
            ]
        )

        post_withdrawal(withdrawal=withdrawal)

    elif destination == Withdrawal.Destination.CASH:

        # Cash withdrawals are posted to the ledger immediately since the
        # cash has already left the till by the time an admin logs it.
        withdrawal.status = Withdrawal.Status.COMPLETED

        from django.utils import timezone
        withdrawal.completed_at = timezone.now()

        withdrawal.save(
            update_fields=["status", "completed_at", "updated_at"]
        )

        post_withdrawal(withdrawal=withdrawal)

    return withdrawal