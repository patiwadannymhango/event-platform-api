from django.urls import path

from apps.payments.providers.lipila.webhooks import (
    LipilaWebhookView,
)

from .views import (
    AdminDashboardView,
    AdminPaymentAccountDetailView,
    AdminPaymentAccountListView,
    AdminPaymentListView,
    AdminPaymentProviderDetailView,
    AdminPaymentProviderListView,
    AdminRefundPaymentView,
    AdminSendMoneyView,
    AdminTransactionListView,
    AdminWalletBalanceView,
    AdminWithdrawalListView,
    AdminWithdrawView,
    InitiatePaymentView,
    PublicBankDetailsView,
    PublicPaymentStatusView,
)

urlpatterns = [

    path(
        "webhooks/lipila/",
        LipilaWebhookView.as_view(),
        name="lipila-webhook",
    ),
    path(
        "public/registrations/<uuid:registration_id>/pay/",
        InitiatePaymentView.as_view(),
        name="initiate-payment",
    ),
    path(
        "public/bank-details/",
        PublicBankDetailsView.as_view(),
        name="public-bank-details",
    ),
    path(
        "public/payments/<uuid:payment_id>/status/",
        PublicPaymentStatusView.as_view(),
        name="public-payment-status",
    ),

    # Admin
    path(
        "admin/events/<uuid:event_id>/dashboard/",
        AdminDashboardView.as_view(),
        name="admin-dashboard",
    ),
    path(
        "admin/events/<uuid:event_id>/wallet/balance/",
        AdminWalletBalanceView.as_view(),
        name="admin-wallet-balance",
    ),
    path(
        "admin/events/<uuid:event_id>/wallet/withdraw/",
        AdminWithdrawView.as_view(),
        name="admin-wallet-withdraw",
    ),
    path(
        "admin/events/<uuid:event_id>/wallet/send-money/",
        AdminSendMoneyView.as_view(),
        name="admin-wallet-send-money",
    ),
    path(
        "admin/events/<uuid:event_id>/withdrawals/",
        AdminWithdrawalListView.as_view(),
        name="admin-withdrawals",
    ),
    path(
        "admin/events/<uuid:event_id>/transactions/",
        AdminTransactionListView.as_view(),
        name="admin-transactions",
    ),
    path(
        "admin/events/<uuid:event_id>/payments/",
        AdminPaymentListView.as_view(),
        name="admin-payments",
    ),
    path(
        "admin/payments/<uuid:payment_id>/refund/",
        AdminRefundPaymentView.as_view(),
        name="admin-refund-payment",
    ),
    path(
        "admin/providers/",
        AdminPaymentProviderListView.as_view(),
        name="admin-payment-provider-list",
    ),
    path(
        "admin/providers/<uuid:provider_id>/",
        AdminPaymentProviderDetailView.as_view(),
        name="admin-payment-provider-detail",
    ),
    path(
        "admin/accounts/",
        AdminPaymentAccountListView.as_view(),
        name="admin-payment-account-list",
    ),
    path(
        "admin/accounts/<uuid:account_id>/",
        AdminPaymentAccountDetailView.as_view(),
        name="admin-payment-account-detail",
    ),

]