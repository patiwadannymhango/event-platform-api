from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Payment,
    Transaction,
)


@transaction.atomic
def post_successful_payment(
    *,
    payment,
):

    payment = (
        Payment.objects
        .select_for_update()
        .get(
            id=payment.id
        )
    )

    if payment.status == (
        Payment.Status.SUCCESS
    ):

        return payment

    transaction_reference = (
        f"TX-{payment.reference}"
    )

    financial_transaction, created = (
        Transaction.objects.get_or_create(
            reference=transaction_reference,
            defaults={
                "wallet": payment.wallet,
                "transaction_type": (
                    Transaction.TransactionType.PAYMENT
                ),
                "direction": (
                    Transaction.Direction.CREDIT
                ),
                "status": (
                    Transaction.Status.POSTED
                ),
                "amount": payment.amount,
                "currency": payment.currency,
                "provider_reference": (
                    payment.provider_reference
                ),
                "description": (
                    "Event registration payment"
                ),
                "metadata": {
                    "payment_id": str(
                        payment.id
                    ),
                    "registration_id": str(
                        payment.registration.id
                    ),
                },
                "posted_at": timezone.now(),
            },
        )
    )

    payment.status = (
        Payment.Status.SUCCESS
    )

    payment.paid_at = (
        timezone.now()
    )

    payment.save(
        update_fields=[
            "status",
            "paid_at",
            "updated_at",
        ]
    )

    return payment


@transaction.atomic
def post_refund(
    *,
    payment,
    amount=None,
    reference=None,
):
    """
    Record a refund against a previously-successful payment: a DEBIT
    transaction on the same wallet, and flips the payment to REFUNDED.
    Does not itself call out to Lipila — see
    apps/payments/services.py:process_refund for the full flow including
    the disbursement call.
    """

    payment = (
        Payment.objects
        .select_for_update()
        .get(id=payment.id)
    )

    refund_amount = amount or payment.amount

    transaction_reference = (
        reference or f"RF-{payment.reference}"
    )

    financial_transaction, created = (
        Transaction.objects.get_or_create(
            reference=transaction_reference,
            defaults={
                "wallet": payment.wallet,
                "transaction_type": Transaction.TransactionType.REFUND,
                "direction": Transaction.Direction.DEBIT,
                "status": Transaction.Status.POSTED,
                "amount": refund_amount,
                "currency": payment.currency,
                "provider_reference": payment.provider_reference,
                "description": "Registration refund",
                "metadata": {
                    "payment_id": str(payment.id),
                    "registration_id": str(payment.registration.id),
                },
                "posted_at": timezone.now(),
            },
        )
    )

    payment.status = Payment.Status.REFUNDED

    payment.save(
        update_fields=["status", "updated_at"]
    )

    return payment, financial_transaction


@transaction.atomic
def post_withdrawal(
    *,
    withdrawal,
):
    """
    Post a DEBIT transaction for a completed withdrawal and link it back
    to the Withdrawal record.
    """

    from .models import Withdrawal  # avoid circular import at module load

    withdrawal = (
        Withdrawal.objects
        .select_for_update()
        .get(id=withdrawal.id)
    )

    financial_transaction, created = (
        Transaction.objects.get_or_create(
            reference=f"WD-{withdrawal.reference}",
            defaults={
                "wallet": withdrawal.wallet,
                "transaction_type": Transaction.TransactionType.WITHDRAWAL,
                "direction": Transaction.Direction.DEBIT,
                "status": Transaction.Status.POSTED,
                "amount": withdrawal.amount,
                "currency": withdrawal.currency,
                "provider_reference": withdrawal.provider_reference,
                "description": withdrawal.narration or "Wallet withdrawal",
                "metadata": {
                    "withdrawal_id": str(withdrawal.id),
                },
                "posted_at": timezone.now(),
            },
        )
    )

    withdrawal.transaction = financial_transaction

    withdrawal.save(
        update_fields=["transaction", "updated_at"]
    )

    return withdrawal, financial_transaction