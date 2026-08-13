import uuid

from .client import LipilaClient
from .phone import normalize_zm_phone


class LipilaProvider:

    def __init__(self):

        self.client = LipilaClient()

    def create_mobile_collection(
        self,
        *,
        reference_id,
        amount,
        account_number,
        currency,
        narration=None,
        reference_data=None,
        callback_url=None,
    ):

        payload = {
            "referenceId": reference_id,
            "amount": float(amount),
            "accountNumber": normalize_zm_phone(account_number),
            "currency": currency,
        }

        if narration:
            payload["narration"] = narration

        if reference_data:
            payload["referenceData"] = (
                reference_data
            )

        return self.client.request(
            "POST",
            "/api/v1/collections/mobile-money",
            data=payload,
            callback_url=callback_url,
        )

    def create_card_collection(
        self,
        *,
        reference_id,
        amount,
        currency,
        first_name,
        last_name,
        phone_number,
        email,
        city,
        address,
        zip_code,
        country="ZM",
        narration=None,
        reference_data=None,
        back_url=None,
        callback_url=None,
    ):
        """
        Card collections are a hosted-checkout redirect, not raw card
        fields — we never see or touch the card number. The response
        carries `cardRedirectionUrl`; the caller sends the browser there,
        the customer enters their card on Lipila's own PCI-compliant
        page, and the outcome comes back the same way mobile money
        does: a webhook to `callback_url`.
        """

        payload = {
            "customerInfo": {
                "firstName": first_name,
                "lastName": last_name,
                "phoneNumber": normalize_zm_phone(phone_number),
                "email": email,
                "city": city,
                "country": country,
                "address": address,
                "zip": zip_code,
            },
            "collectionRequest": {
                "referenceId": reference_id,
                "amount": float(amount),
                "currency": currency,
                "accountNumber": normalize_zm_phone(phone_number),
                "narration": narration or "Event registration payment",
                "backUrl": back_url or "",
                "referenceData": reference_data or reference_id,
            },
        }

        return self.client.request(
            "POST",
            "/api/v1/collections/card",
            data=payload,
            callback_url=callback_url,
        )

    def get_collection_status(
        self,
        *,
        reference_id,
    ):

        return self.client.request(
            "GET",
            "/api/v1/collections/check-status",
            params={
                "referenceId": reference_id,
            },
        )

    def create_disbursement(
        self,
        *,
        reference_id,
        amount,
        account_number,
        currency,
        full_name=None,
        phone_number=None,
        email=None,
        narration=None,
    ):
        """
        Send money out to a mobile money account — used for withdrawals
        and refunds. Endpoint path is configurable via
        settings.LIPILA_DISBURSEMENT_ENDPOINT: confirm the exact path and
        payload shape against your Lipila merchant dashboard before
        relying on this in production, since Lipila's docs describe more
        than one API generation.
        """

        from django.conf import settings

        payload = {
            "referenceId": reference_id,
            "externalId": reference_id,
            "amount": float(amount),
            "accountNumber": normalize_zm_phone(account_number),
            "currency": currency,
        }

        if full_name:
            payload["fullName"] = full_name

        if phone_number:
            payload["phoneNumber"] = normalize_zm_phone(phone_number)

        if email:
            payload["email"] = email

        if narration:
            payload["narration"] = narration

        return self.client.request(
            "POST",
            settings.LIPILA_DISBURSEMENT_ENDPOINT,
            data=payload,
        )

    def get_balance(self):
        """
        Fetch the merchant account's current float balance. Endpoint path
        is configurable via settings.LIPILA_BALANCE_ENDPOINT — confirm
        against your Lipila dashboard.
        """

        from django.conf import settings

        return self.client.request(
            "GET",
            settings.LIPILA_BALANCE_ENDPOINT,
        )