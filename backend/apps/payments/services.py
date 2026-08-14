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


def apply_payment_outcome(
    *,
    payment,
    provider_status,
    raw_response=None,
    response_key="provider_check",
):
    """
    Shared success/failure transition for a Payment, driven by whatever
    Lipila reports — used by both the webhook (push, in
    providers/lipila/webhooks.py) and sync_payment_status_from_lipila
    below (pull, called while the frontend is polling), so a missed or
    delayed webhook doesn't leave a payment stuck on PENDING/PROCESSING
    forever even though Lipila already settled it on their end.
    """

    from .models import Payment as PaymentModel

    if raw_response is not None:
        payment.provider_response = {
            **payment.provider_response,
            response_key: raw_response,
        }
        payment.save(update_fields=["provider_response", "updated_at"])

    settled_states = (
        PaymentModel.Status.SUCCESS,
        PaymentModel.Status.FAILED,
        PaymentModel.Status.REFUNDED,
        PaymentModel.Status.CANCELLED,
    )

    if payment.status in settled_states:
        # Already settled — never re-process. Guards against the webhook
        # and an active poll-time check both resolving around the same
        # moment (would otherwise double-credit the wallet or double-send
        # the confirmation notification).
        return payment

    provider_status = (provider_status or "").upper()

    success_states = {"SUCCESS", "SUCCESSFUL", "COMPLETED", "PAID"}
    failed_states = {"FAILED", "FAILURE", "CANCELLED", "DECLINED"}

    if provider_status in success_states:

        from .ledger import post_successful_payment
        from apps.registrations.models import Registration

        with transaction.atomic():
            payment = post_successful_payment(payment=payment)

            registration = payment.registration
            registration.status = Registration.Status.CONFIRMED
            registration.save(update_fields=["status", "updated_at"])

        from apps.notifications.services import notify_payment_confirmed
        notify_payment_confirmed(payment.registration)

    elif provider_status in failed_states:

        payment.status = PaymentModel.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])

        from apps.notifications.services import notify_payment_failed
        notify_payment_failed(payment.registration, reason=provider_status)

    # Anything else (still pending/processing on Lipila's side — e.g. a
    # bank still finalising a card charge) is left exactly as-is: no
    # status flip, no notification, until a definitive outcome arrives.

    return payment


def sync_payment_status_from_lipila(payment):
    """
    Actively re-check a still-in-flight payment against Lipila instead of
    only waiting on their webhook. Called from the status-polling
    endpoint the frontend hits while showing the "waiting" screen, so a
    payment that actually succeeded (or failed) on Lipila's side gets
    picked up on the next poll even if the webhook for it was delayed,
    dropped, or never sent at all — the gap that otherwise leaves the
    frontend stuck on "waiting" after a real-world redirect-back from a
    card payment. Safe to call on every poll: a no-op once the payment is
    settled, and any Lipila API failure here is swallowed so a flaky
    provider call never breaks the poll itself.
    """

    from .models import Payment as PaymentModel

    if payment.status != PaymentModel.Status.PROCESSING:
        # PENDING means no Lipila collection exists yet to check (or this
        # is a bank transfer, which never goes through Lipila at all —
        # those are reconciled manually against the bank statement).
        # Anything else is already settled.
        return payment

    if payment.provider.provider_type != "LIPILA":
        return payment

    from .providers.lipila.client import LipilaAPIError
    from .providers.lipila.services import LipilaProvider

    try:
        response = LipilaProvider().get_collection_status(
            reference_id=payment.reference,
        )
    except LipilaAPIError:
        return payment
    except Exception:  # noqa: BLE001 — a flaky status check must never break polling
        return payment

    return apply_payment_outcome(
        payment=payment,
        provider_status=response.get("status", ""),
        raw_response=response,
        response_key="lipila_status_check",
    )


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