from django.db import models

from apps.common.models import UUIDModel
from decimal import Decimal
from django.core.validators import MinValueValidator

from django.db.models import Sum



class PaymentMethod(models.TextChoices):

    MOBILE_MONEY = (
        "MOBILE_MONEY",
        "Mobile Money",
    )

    CARD = (
        "CARD",
        "Card",
    )

    MTN_MONEY = (
        "MTN_MONEY",
        "MTN Money",
    )

    AIRTEL_MONEY = (
        "AIRTEL_MONEY",
        "Airtel Money",
    )

    ZAMTEL_KWACHA = (
        "ZAMTEL_KWACHA",
        "Zamtel Kwacha",
    )

    VISA = (
        "VISA",
        "Visa",
    )

    MASTERCARD = (
        "MASTERCARD",
        "Mastercard",
    )

    AMERICAN_EXPRESS = (
        "AMERICAN_EXPRESS",
        "American Express",
    )

    BANK_TRANSFER = (
        "BANK_TRANSFER",
        "Bank Transfer",
    )



class PaymentProvider(UUIDModel):

    class ProviderType(models.TextChoices):
        LIPILA = "LIPILA", "Lipila"
        OTHER = "OTHER", "Other"

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    provider_type = models.CharField(
        max_length=30,
        choices=ProviderType.choices,
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
        return self.name


    
class PaymentAccount(UUIDModel):

    class AccountType(models.TextChoices):
        WALLET = "WALLET", "Wallet"
        MERCHANT = "MERCHANT", "Merchant"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="payment_accounts",
    )

    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name="payment_accounts",
    )

    account_type = models.CharField(
        max_length=30,
        choices=AccountType.choices,
        default=AccountType.WALLET,
    )

    name = models.CharField(
        max_length=150,
    )

    provider_account_id = models.CharField(
        max_length=255,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="ZMW",
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
                    "organization",
                    "provider",
                    "provider_account_id",
                ],
                name="unique_provider_account",
            )
        ]

    def __str__(self):
        return self.name
    

class Wallet(UUIDModel):

    event = models.OneToOneField(
        "events.Event",
        on_delete=models.PROTECT,
        related_name="wallet",
    )

    currency = models.CharField(
        max_length=10,
        default="ZMW",
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

    @property
    def posted_credits(self):

        result = self.transactions.filter(
            status=Transaction.Status.POSTED,
            direction=Transaction.Direction.CREDIT,
        ).aggregate(
            total=Sum("amount")
        )

        return result["total"] or Decimal("0.00")


    @property
    def posted_debits(self):

        result = self.transactions.filter(
            status=Transaction.Status.POSTED,
            direction=Transaction.Direction.DEBIT,
        ).aggregate(
            total=Sum("amount")
        )

        return result["total"] or Decimal("0.00")


    @property
    def balance(self):

        return (
            self.posted_credits
            - self.posted_debits
        )



    @property
    def pending_balance(self):

        result = self.transactions.filter(
            status=Transaction.Status.PENDING,
            direction=Transaction.Direction.CREDIT,
        ).aggregate(
            total=Sum("amount")
        )

        return result["total"] or Decimal("0.00")

    

    def __str__(self):
        return (
            f"{self.event.name} Wallet"
        )


class Payment(UUIDModel):

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    registration = models.ForeignKey(
        "registrations.Registration",
        on_delete=models.PROTECT,
        related_name="payments",
    )

    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    payment_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="ZMW",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CREATED,
    )

    # payment_method = models.CharField(
    #     max_length=50,
    #     blank=True,
    # )
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
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
            "-created_at",
        ]

    def __str__(self):
        return self.reference


    
# class Transaction(UUIDModel):

#     class TransactionType(models.TextChoices):
#         CREDIT = "CREDIT", "Credit"
#         DEBIT = "DEBIT", "Debit"
#         FEE = "FEE", "Fee"
#         REFUND = "REFUND", "Refund"
#         REVERSAL = "REVERSAL", "Reversal"

#     class Status(models.TextChoices):
#         PENDING = "PENDING", "Pending"
#         POSTED = "POSTED", "Posted"
#         FAILED = "FAILED", "Failed"
#         REVERSED = "REVERSED", "Reversed"

#     payment_account = models.ForeignKey(
#         PaymentAccount,
#         on_delete=models.PROTECT,
#         related_name="transactions",
#     )

#     payment = models.ForeignKey(
#         Payment,
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True,
#         related_name="transactions",
#     )

#     reference = models.CharField(
#         max_length=100,
#         unique=True,
#         db_index=True,
#     )

#     transaction_type = models.CharField(
#         max_length=30,
#         choices=TransactionType.choices,
#     )

#     status = models.CharField(
#         max_length=30,
#         choices=Status.choices,
#         default=Status.POSTED,
#     )

#     amount = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#     )

#     currency = models.CharField(
#         max_length=3,
#         default="ZMW",
#     )

#     description = models.CharField(
#         max_length=255,
#         blank=True,
#     )

#     provider_transaction_id = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#     )

#     metadata = models.JSONField(
#         default=dict,
#         blank=True,
#     )

#     transaction_date = models.DateTimeField()

#     created_at = models.DateTimeField(
#         auto_now_add=True,
#     )

#     class Meta:
#         ordering = [
#             "-transaction_date",
#         ]

#     def __str__(self):
#         return self.reference


# class Transaction(UUIDModel):

#     class TransactionType(models.TextChoices):
#         CREDIT = "CREDIT", "Credit"
#         DEBIT = "DEBIT", "Debit"
#         FEE = "FEE", "Fee"
#         REFUND = "REFUND", "Refund"
#         REVERSAL = "REVERSAL", "Reversal"

#     class Status(models.TextChoices):
#         PENDING = "PENDING", "Pending"
#         POSTED = "POSTED", "Posted"
#         FAILED = "FAILED", "Failed"
#         REVERSED = "REVERSED", "Reversed"

#     payment_account = models.ForeignKey(
#         PaymentAccount,
#         on_delete=models.PROTECT,
#         related_name="transactions",
#     )

#     payment = models.ForeignKey(
#         Payment,
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True,
#         related_name="transactions",
#     )

#     reference = models.CharField(
#         max_length=100,
#         unique=True,
#         db_index=True,
#     )

#     transaction_type = models.CharField(
#         max_length=30,
#         choices=TransactionType.choices,
#     )

#     status = models.CharField(
#         max_length=30,
#         choices=Status.choices,
#         default=Status.POSTED,
#     )

#     amount = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#     )

#     currency = models.CharField(
#         max_length=3,
#         default="ZMW",
#     )

#     description = models.CharField(
#         max_length=255,
#         blank=True,
#     )

#     provider_transaction_id = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#     )

#     metadata = models.JSONField(
#         default=dict,
#         blank=True,
#     )

#     transaction_date = models.DateTimeField()

#     created_at = models.DateTimeField(
#         auto_now_add=True,
#     )

#     class Meta:
#         ordering = [
#             "-transaction_date",
#         ]

#     def __str__(self):
#         return self.reference



class Withdrawal(UUIDModel):

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Destination(models.TextChoices):
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        BANK = "BANK", "Bank Account"
        CASH = "CASH", "Cash"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="withdrawals",
    )

    transaction = models.OneToOneField(
        "Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawal",
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    destination = models.CharField(
        max_length=30,
        choices=Destination.choices,
        default=Destination.MOBILE_MONEY,
    )

    destination_account = models.CharField(
        max_length=150,
        help_text="Phone number, bank account, or note for cash withdrawal.",
    )

    recipient_name = models.CharField(
        max_length=150,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="ZMW",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )

    narration = models.CharField(
        max_length=255,
        blank=True,
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawals_requested",
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-requested_at",
        ]

    def __str__(self):
        return (
            f"{self.reference} "
            f"{self.amount} {self.currency} "
            f"({self.status})"
        )


class Transaction(UUIDModel):

    class TransactionType(models.TextChoices):

        PAYMENT = (
            "PAYMENT",
            "Payment",
        )

        WITHDRAWAL = (
            "WITHDRAWAL",
            "Withdrawal",
        )

        REFUND = (
            "REFUND",
            "Refund",
        )

        FEE = (
            "FEE",
            "Fee",
        )

        ADJUSTMENT = (
            "ADJUSTMENT",
            "Adjustment",
        )

    class Direction(models.TextChoices):

        CREDIT = (
            "CREDIT",
            "Credit",
        )

        DEBIT = (
            "DEBIT",
            "Debit",
        )

    class Status(models.TextChoices):

        PENDING = (
            "PENDING",
            "Pending",
        )

        POSTED = (
            "POSTED",
            "Posted",
        )

        FAILED = (
            "FAILED",
            "Failed",
        )

        REVERSED = (
            "REVERSED",
            "Reversed",
        )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=30,
        choices=TransactionType.choices,
    )

    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01")
            )
        ],
    )

    currency = models.CharField(
        max_length=10,
        default="ZMW",
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    posted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "wallet",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "transaction_type",
                ]
            ),
            models.Index(
                fields=[
                    "provider_reference",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.reference} "
            f"{self.amount} "
            f"{self.direction}"
        )