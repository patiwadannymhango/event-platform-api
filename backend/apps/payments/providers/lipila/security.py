import base64
import hashlib
import hmac
import time

from django.conf import settings


class InvalidLipilaWebhook(Exception):
    pass


def verify_lipila_webhook(
    *,
    webhook_id,
    webhook_timestamp,
    webhook_signature,
    raw_body,
):

    if not all(
        [
            webhook_id,
            webhook_timestamp,
            webhook_signature,
        ]
    ):
        raise InvalidLipilaWebhook(
            "Missing webhook security headers."
        )

    try:

        timestamp = int(
            webhook_timestamp
        )

    except ValueError:

        raise InvalidLipilaWebhook(
            "Invalid webhook timestamp."
        )

    # Prevent very old/replayed requests.
    tolerance = 300

    if abs(
        time.time() - timestamp
    ) > tolerance:

        raise InvalidLipilaWebhook(
            "Webhook timestamp is too old."
        )

    signed_payload = (
        f"{webhook_id}."
        f"{webhook_timestamp}."
    ).encode() + raw_body

    secret = (
        settings.LIPILA_WEBHOOK_SECRET
    )

    try:

        secret_bytes = base64.b64decode(
            secret
        )

    except Exception:

        raise InvalidLipilaWebhook(
            "Invalid webhook secret."
        )

    digest = hmac.new(
        secret_bytes,
        signed_payload,
        hashlib.sha256,
    ).digest()

    expected_signature = base64.b64encode(
        digest
    ).decode()

    signatures = (
        webhook_signature.split(" ")
    )

    valid = False

    for signature in signatures:

        if not signature.startswith("v1,"):
            continue

        received_signature = (
            signature.split(",", 1)[1]
        )

        if hmac.compare_digest(
            received_signature,
            expected_signature,
        ):

            valid = True
            break

    if not valid:

        raise InvalidLipilaWebhook(
            "Invalid webhook signature."
        )

    return True