from django.contrib import admin

from .models import (
    Payment,
    PaymentAccount,
    PaymentProvider,
    Transaction,
    Wallet,
    Withdrawal,
)


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "provider_type", "is_active")
    list_filter = ("provider_type", "is_active")
    search_fields = ("name", "code")


@admin.register(PaymentAccount)
class PaymentAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "provider", "currency", "is_active")
    list_filter = ("provider", "currency", "is_active")
    search_fields = ("name", "organization__name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "registration",
        "amount",
        "currency",
        "status",
        "provider",
        "created_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = (
        "reference",
        "provider_reference",
        "registration__registration_number",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "wallet",
        "transaction_type",
        "direction",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("transaction_type", "direction", "status", "currency")
    search_fields = ("reference", "provider_reference", "description")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("event", "currency", "balance", "pending_balance", "is_active")
    readonly_fields = ("balance", "pending_balance")


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "wallet",
        "amount",
        "currency",
        "status",
        "destination",
        "requested_by",
        "requested_at",
    )
    list_filter = ("status", "destination", "currency")
    search_fields = ("reference", "provider_reference")
    readonly_fields = ("requested_at", "completed_at", "updated_at")
