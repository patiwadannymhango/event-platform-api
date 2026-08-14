import json

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import (
    Payment,
)

from apps.payments.services import (
    apply_payment_outcome,
)

from .security import (
    InvalidLipilaWebhook,
    verify_lipila_webhook,
)


class LipilaWebhookView(APIView):

    permission_classes = [
        AllowAny,
    ]

    authentication_classes = []

    def post(
        self,
        request,
    ):

        webhook_id = request.headers.get(
            "webhook-id"
        )

        webhook_timestamp = (
            request.headers.get(
                "webhook-timestamp"
            )
        )

        webhook_signature = (
            request.headers.get(
                "webhook-signature"
            )
        )

        try:

            verify_lipila_webhook(
                webhook_id=webhook_id,
                webhook_timestamp=(
                    webhook_timestamp
                ),
                webhook_signature=(
                    webhook_signature
                ),
                raw_body=request.body,
            )

        except InvalidLipilaWebhook:

            return Response(
                {
                    "detail": (
                        "Invalid webhook."
                    )
                },
                status=401,
            )

        data = json.loads(
            request.body
        )

        self._process(data)

        return Response(
            {
                "status": "received"
            }
        )

    def _process(self, data):
        """
        Look up the Payment this webhook refers to and post the outcome.

        Per Lipila's docs (docs.lipila.io/docs/billing/webhook.html), the
        payload is: referenceId, currency, amount, accountNumber, status
        ("Successful"/"Failed"), paymentType, type, identifier, message,
        externalId (optional), referenceData (optional) — the same shape
        for both mobile money and card collections.

        We set `referenceId` to our own Payment.reference (e.g.
        "PAY-...") when creating the collection, and Lipila has been
        observed echoing it back unchanged. `referenceData` carries our
        registration number as a second, independent way to find the
        right payment in case that ever isn't true.
        """

        candidate_refs = [
            value
            for value in (
                data.get("referenceId"),
                data.get("identifier"),
                data.get("externalId"),
            )
            if value
        ]

        payment = None

        for ref in candidate_refs:
            payment = (
                Payment.objects
                .filter(reference=ref)
                .first()
                or Payment.objects
                .filter(provider_reference=ref)
                .first()
            )
            if payment:
                break

        if not payment and data.get("referenceData"):

            payment = (
                Payment.objects
                .filter(
                    registration__registration_number=(
                        data["referenceData"]
                    )
                )
                .order_by("-created_at")
                .first()
            )

        if not payment:
            return

        apply_payment_outcome(
            payment=payment,
            provider_status=data.get("status") or "",
            raw_response=data,
            response_key="webhook",
        )