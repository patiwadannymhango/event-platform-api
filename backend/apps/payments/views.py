from django.conf import settings

from rest_framework import status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.access import (
    EVENT_FINANCE_ROLES,
    EVENT_VIEW_ROLES,
    require_event_role,
)
from apps.common.permissions import HasEventRole, IsSuperUser
from apps.registrations.models import (
    Registration,
)

from .providers.lipila.client import (
    LipilaAPIError,
)
from .serializers import (
    InitiatePaymentSerializer,
)
from .services import (
    create_payment,
    initiate_card_payment,
    initiate_mobile_payment,
)


def _fail_payment(payment, exc):
    """
    Shared failure path for both mobile money and card collection
    attempts: mark the payment FAILED (so it doesn't sit as a phantom
    PENDING/PROCESSING row forever) and surface Lipila's actual reason
    to the caller instead of a generic 500.
    """

    payment.status = payment.Status.FAILED
    payment.provider_response = {
        **payment.provider_response,
        "error": str(exc.args[0]),
    }
    payment.save(
        update_fields=[
            "status",
            "provider_response",
            "updated_at",
        ]
    )

    return Response(
        {"detail": _lipila_error_message(exc)},
        status=status.HTTP_502_BAD_GATEWAY,
    )


def _lipila_error_message(exc):
    """
    Turn a LipilaAPIError's raw response payload into a message the
    runner can actually act on (e.g. "Invalid phone number format"),
    instead of a generic failure with no explanation.
    """

    payload = exc.args[0] if exc.args else {}

    if isinstance(payload, dict):

        errors = payload.get("errors")

        if isinstance(errors, dict) and errors:
            first_value = next(iter(errors.values()))
            if isinstance(first_value, list) and first_value:
                return str(first_value[0])
            return str(first_value)

        if payload.get("message"):
            return str(payload["message"])

    return (
        "The payment provider rejected this request. "
        "Please check the details and try again."
    )


class PublicBankDetailsView(APIView):
    """
    GET /api/v1/payments/public/bank-details/

    Bank account details for runners paying by bank transfer, kept
    server-side in settings/.env so they can be corrected without a
    frontend deploy.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from django.conf import settings
        return Response(settings.BANK_ACCOUNT_DETAILS)


class PublicPaymentStatusView(APIView):
    """
    GET /api/v1/payments/public/payments/<payment_id>/status/

    Polled by the frontend while a mobile money prompt is on the runner's
    phone (or while waiting on a card payment redirect), so it knows when
    to stop showing the "waiting" screen. Each poll also actively
    re-verifies with Lipila (sync_payment_status_from_lipila) rather than
    only trusting whatever the webhook has already written to our own
    database — a card payment in particular can settle on Lipila's side
    with the webhook for it arriving late or not at all, which otherwise
    leaves this endpoint (and the frontend polling it) reporting PENDING
    forever even though the transaction actually went through.
    """

    permission_classes = [AllowAny]

    def get(self, request, payment_id):

        from .models import Payment as PaymentModel
        from .services import sync_payment_status_from_lipila

        try:

            payment = (
                PaymentModel.objects
                .select_related("registration")
                .get(id=payment_id)
            )

        except PaymentModel.DoesNotExist:

            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payment = sync_payment_status_from_lipila(payment)

        return Response(
            {
                "status": payment.status,
                "registration_status": (
                    payment.registration.status
                ),
                "amount": str(payment.amount),
                "currency": payment.currency,
            }
        )


class InitiatePaymentView(APIView):

    permission_classes = [
        AllowAny,
    ]

    def post(
        self,
        request,
        registration_id,
    ):

        try:

            registration = (
                Registration.objects.get(
                    id=registration_id,
                )
            )

        except Registration.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "Registration not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if registration.status != (
            Registration.Status.PENDING_PAYMENT
        ):

            return Response(
                {
                    "detail": (
                        "This registration "
                        "cannot accept payment."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = (
            InitiatePaymentSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        method = serializer.validated_data[
            "payment_method"
        ]

        payment = create_payment(
            registration=registration,
            payment_method=method,
        )

        redirect_url = ""

        callback_url = (
            f"{settings.PUBLIC_BASE_URL}/api/v1/payments/webhooks/lipila/"
            if settings.PUBLIC_BASE_URL
            else request.build_absolute_uri(
                "/api/v1/payments/webhooks/lipila/"
            )
        )

        if method in ("MTN_MONEY", "AIRTEL_MONEY", "ZAMTEL_KWACHA"):

            try:

                payment = initiate_mobile_payment(
                    payment=payment,
                    phone_number=(
                        serializer.validated_data[
                            "phone_number"
                        ]
                    ),
                    callback_url=callback_url,
                )

            except LipilaAPIError as exc:

                return _fail_payment(
                    payment, exc
                )

        elif method == "CARD":

            back_url = (
                request.data.get("back_url")
                or callback_url
            )

            try:

                payment, redirect_url = (
                    initiate_card_payment(
                        payment=payment,
                        participant=(
                            registration.participant
                        ),
                        city=serializer.validated_data.get(
                            "city", ""
                        ),
                        address=serializer.validated_data.get(
                            "address", ""
                        ),
                        zip_code=serializer.validated_data.get(
                            "zip_code", ""
                        ),
                        country=serializer.validated_data.get(
                            "country", "ZM"
                        ),
                        callback_url=callback_url,
                        back_url=back_url,
                    )
                )

            except LipilaAPIError as exc:

                return _fail_payment(
                    payment, exc
                )

        elif method == "BANK_TRANSFER":

            # No Lipila call for bank transfer — just record who to expect
            # the transfer from, so admins can reconcile it against the
            # bank statement.
            payment.provider_response = {
                **payment.provider_response,
                "bank_transfer": {
                    "payer_name": serializer.validated_data.get(
                        "payer_name", ""
                    ),
                    "transfer_reference": serializer.validated_data.get(
                        "transfer_reference", ""
                    ),
                },
            }

            payment.save(
                update_fields=[
                    "provider_response",
                    "updated_at",
                ]
            )

        return Response(
            {
                "payment": {
                    "id": payment.id,
                    "reference": (
                        payment.reference
                    ),
                    "provider_reference": (
                        payment.provider_reference
                    ),
                    "amount": str(
                        payment.amount
                    ),
                    "currency": (
                        payment.currency
                    ),
                    "status": (
                        payment.status
                    ),
                    "payment_method": (
                        payment.payment_method
                    ),
                    "redirect_url": redirect_url,
                }
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin-facing views
# ---------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation

from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Payment as PaymentModel,
    PaymentAccount,
    PaymentProvider,
    Transaction,
    Wallet,
    Withdrawal,
)
from .serializers import (
    PaymentSerializer,
    RefundRequestSerializer,
    SendMoneySerializer,
    TransactionSerializer,
    WalletSerializer,
    WithdrawalRequestSerializer,
    WithdrawalSerializer,
)
from .services import get_live_balance, process_refund, request_withdrawal


def _event_wallet(event):
    wallet, _ = Wallet.objects.get_or_create(event=event)
    return wallet


class AdminWalletBalanceView(APIView):
    """
    GET /api/v1/payments/admin/events/<event_id>/wallet/balance/

    Returns the ledger balance always, and attempts a live Lipila balance
    call as well — if Lipila is unreachable the ledger balance is still
    returned so the dashboard doesn't just break.
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]

    def get(self, request, event_id):
        from apps.events.models import Event

        event = Event.objects.get(id=event_id)
        wallet = _event_wallet(event)

        data = {
            "ledger_balance": str(wallet.balance),
            "pending_balance": str(wallet.pending_balance),
            "currency": wallet.currency,
            "live_balance": None,
            "live_balance_error": None,
        }

        if event.payment_account:
            try:
                live = get_live_balance(event.payment_account)
                data["live_balance"] = live
            except Exception as exc:  # noqa: BLE001
                data["live_balance_error"] = str(exc)

        return Response(data)


class AdminDashboardView(APIView):
    """
    GET /api/v1/payments/admin/events/<event_id>/dashboard/

    One-stop summary for the admin dashboard: registration counts by
    status, revenue collected vs pending, and wallet balance.
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]

    def get(self, request, event_id):
        from datetime import timedelta

        from django.db.models import Sum, Count
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from apps.registrations.models import Registration

        registrations = Registration.objects.filter(event_id=event_id)

        by_status = list(
            registrations.values("status").annotate(count=Count("id"))
        )

        today_count = registrations.filter(
            registered_at__date=timezone.localdate()
        ).count()

        revenue_confirmed = (
            registrations.filter(status=Registration.Status.CONFIRMED)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        revenue_pending = (
            registrations.filter(
                status__in=[
                    Registration.Status.PENDING_PAYMENT,
                    Registration.Status.PAYMENT_PROCESSING,
                    Registration.Status.RESERVED,
                ]
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        wallet, _ = Wallet.objects.get_or_create(event_id=event_id)

        # --- Chart data (admin dashboards) ---

        since = timezone.localdate() - timedelta(days=13)  # 14 days, inclusive of today

        daily_qs = (
            registrations
            .filter(registered_at__date__gte=since)
            .annotate(day=TruncDate("registered_at"))
            .values("day", "status")
            .annotate(count=Count("id"))
        )

        daily_buckets = {}
        for row in daily_qs:
            bucket = daily_buckets.setdefault(
                row["day"].isoformat(), {"confirmed": 0, "other": 0}
            )
            if row["status"] == Registration.Status.CONFIRMED:
                bucket["confirmed"] += row["count"]
            else:
                bucket["other"] += row["count"]

        daily_registrations = []
        for offset in range(14):
            day = (since + timedelta(days=offset)).isoformat()
            bucket = daily_buckets.get(day, {"confirmed": 0, "other": 0})
            daily_registrations.append({"date": day, **bucket})

        by_category = [
            {"name": row["category__name"], "count": row["count"]}
            for row in (
                registrations
                .values("category__name")
                .annotate(count=Count("id"))
                .order_by("-count")
            )
        ]

        by_country = [
            {"country": row["form_data__country"], "count": row["count"]}
            for row in (
                registrations
                .exclude(form_data__country__isnull=True)
                .exclude(form_data__country="")
                .values("form_data__country")
                .annotate(count=Count("id"))
                .order_by("-count")
            )
        ]

        return Response(
            {
                "total_registrations": registrations.count(),
                "today_count": today_count,
                "by_status": by_status,
                "revenue_confirmed": str(revenue_confirmed),
                "revenue_pending": str(revenue_pending),
                "wallet_balance": str(wallet.balance),
                "wallet_pending_balance": str(wallet.pending_balance),
                "daily_registrations": daily_registrations,
                "by_category": by_category,
                "by_country": by_country,
            }
        )


class AdminTransactionListView(ListAPIView):
    """GET /api/v1/payments/admin/events/<event_id>/transactions/"""

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["transaction_type", "direction", "status"]
    search_fields = ["reference", "provider_reference", "description"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        return Transaction.objects.filter(
            wallet__event_id=self.kwargs["event_id"]
        )


class AdminPaymentListView(ListAPIView):
    """GET /api/v1/payments/admin/events/<event_id>/payments/"""

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "payment_method"]
    search_fields = ["reference", "provider_reference", "registration__registration_number"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        return PaymentModel.objects.filter(
            registration__event_id=self.kwargs["event_id"]
        )


class AdminWithdrawalListView(ListAPIView):
    """GET /api/v1/payments/admin/events/<event_id>/withdrawals/"""

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]
    serializer_class = WithdrawalSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "destination"]
    ordering_fields = ["requested_at", "amount"]

    def get_queryset(self):
        return Withdrawal.objects.filter(
            wallet__event_id=self.kwargs["event_id"]
        )


class AdminWithdrawView(APIView):
    """
    POST /api/v1/payments/admin/events/<event_id>/wallet/withdraw/

    Withdraw event funds out to the organiser's own mobile money number
    (or record a bank/cash withdrawal for manual reconciliation).
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_FINANCE_ROLES)]

    def post(self, request, event_id):
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(event_id=event_id)
        data = serializer.validated_data

        if data["amount"] > wallet.balance:
            return Response(
                {"detail": "Withdrawal amount exceeds available balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            withdrawal = request_withdrawal(
                wallet=wallet,
                amount=data["amount"],
                destination=data["destination"],
                destination_account=data["destination_account"],
                recipient_name=data.get("recipient_name", ""),
                narration=data.get("narration", ""),
                requested_by=request.user,
            )
        except LipilaAPIError as exc:
            return Response(
                {"detail": _lipila_error_message(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED,
        )


class AdminSendMoneyView(APIView):
    """
    POST /api/v1/payments/admin/events/<event_id>/wallet/send-money/

    Ad-hoc disbursement to any mobile money number — e.g. paying a
    supplier or correcting a manual error. Recorded as a Withdrawal so it
    appears in the same audit trail.
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_FINANCE_ROLES)]

    def post(self, request, event_id):
        serializer = SendMoneySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(event_id=event_id)
        data = serializer.validated_data

        if data["amount"] > wallet.balance:
            return Response(
                {"detail": "Amount exceeds available balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            withdrawal = request_withdrawal(
                wallet=wallet,
                amount=data["amount"],
                destination=Withdrawal.Destination.MOBILE_MONEY,
                destination_account=data["account_number"],
                recipient_name=data.get("recipient_name", ""),
                narration=data.get("narration", "Manual send money"),
                requested_by=request.user,
            )
        except LipilaAPIError as exc:
            return Response(
                {"detail": _lipila_error_message(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED,
        )


class AdminRefundPaymentView(APIView):
    """POST /api/v1/payments/admin/payments/<payment_id>/refund/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        try:
            payment = PaymentModel.objects.select_related(
                "registration"
            ).get(id=payment_id)
        except PaymentModel.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Not keyed by event_id in the URL, so the role check has to
        # happen here rather than via a HasEventRole permission class —
        # same pattern EventDetailView.get_object() uses.
        require_event_role(
            request.user,
            payment.registration.event_id,
            *EVENT_FINANCE_ROLES,
        )

        if payment.status != PaymentModel.Status.SUCCESS:
            return Response(
                {"detail": "Only successful payments can be refunded."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data.get("amount")

        try:
            payment, txn, provider_response = process_refund(
                payment=payment,
                amount=amount,
                requested_by=request.user,
            )
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"detail": f"Refund failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        from apps.notifications.services import notify_refund_processed

        notify_refund_processed(payment.registration, amount=txn.amount)

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "transaction": TransactionSerializer(txn).data,
            }
        )


# ---------------------------------------------------------------------------
# Payment provider/account management — superuser only, since these hold
# the merchant/provider configuration events get paid through. Built
# here rather than in apps/payment_providers, which has no models of its
# own and isn't wired into config/urls.py.
# ---------------------------------------------------------------------------

from .serializers import PaymentAccountSerializer, PaymentProviderSerializer


class AdminPaymentProviderListView(ListAPIView):
    """GET/POST /api/v1/payments/admin/providers/"""

    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = PaymentProviderSerializer
    queryset = PaymentProvider.objects.all().order_by("name")

    def post(self, request):
        serializer = PaymentProviderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.save()
        return Response(
            PaymentProviderSerializer(provider).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPaymentProviderDetailView(APIView):
    """PATCH /api/v1/payments/admin/providers/<provider_id>/"""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def patch(self, request, provider_id):
        from django.shortcuts import get_object_or_404

        provider = get_object_or_404(PaymentProvider, id=provider_id)
        serializer = PaymentProviderSerializer(
            provider, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PaymentProviderSerializer(provider).data)


class AdminPaymentAccountListView(ListAPIView):
    """GET/POST /api/v1/payments/admin/accounts/"""

    permission_classes = [IsAuthenticated, IsSuperUser]
    serializer_class = PaymentAccountSerializer
    queryset = PaymentAccount.objects.select_related(
        "organization", "provider"
    ).order_by("name")

    def post(self, request):
        serializer = PaymentAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        return Response(
            PaymentAccountSerializer(account).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPaymentAccountDetailView(APIView):
    """PATCH /api/v1/payments/admin/accounts/<account_id>/"""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def patch(self, request, account_id):
        from django.shortcuts import get_object_or_404

        account = get_object_or_404(PaymentAccount, id=account_id)
        serializer = PaymentAccountSerializer(
            account, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PaymentAccountSerializer(account).data)