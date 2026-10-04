"""
Pluggable SMS sending.

The Africa's Talking backend is implemented and ready — flipping
SMS_BACKEND=africastalking in .env (with AFRICASTALKING_USERNAME /
AFRICASTALKING_API_KEY set) is enough to go live for every automatic
notification (registration received, payment confirmed) that already
calls send_sms(). Until that flag is flipped, SMS_BACKEND defaults to
"console", which just logs the message via the Notification model
(status=SENT, provider_response={"backend": "console"}) without
actually dispatching anything — this is still the live production
setting as of the first Africa's Talking integration (sandbox
credentials only), deliberately, so a real confirmation event doesn't
start texting the general public before that's an explicit decision.
"""

from django.conf import settings
from django.utils import timezone

from .models import Notification


def _send_console(*, to, message):
    print(f"[SMS -> {to}] {message}")  # noqa: T201 — intentional dev stand-in
    return {"backend": "console"}


def _to_e164(phone):
    """
    Africa's Talking rejects anything that isn't +<countrycode><number> —
    most phone numbers stored on a registration are local Zambian format
    (0977xxxxxx), some are already +260977xxxxxx (the public form accepts
    either). Assumes Zambia (+260) for a bare local number, since that's
    this event's whole audience; doesn't touch a number that already has
    a country code.
    """
    digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if digits.startswith("+"):
        return digits
    if digits.startswith("0"):
        return "+260" + digits[1:]
    if digits.startswith("260"):
        return "+" + digits
    return "+260" + digits


_at_initialized = False


def _send_africastalking(*, to, message):
    global _at_initialized
    import africastalking

    if not _at_initialized:
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY,
        )
        _at_initialized = True

    sender_id = settings.SMS_SENDER_ID or None
    response = africastalking.SMS.send(message, [_to_e164(to)], sender_id=sender_id)
    return response


BACKENDS = {
    "console": _send_console,
    "africastalking": _send_africastalking,
}


def send_sms(
    *,
    to,
    message,
    registration=None,
    notification_type=Notification.NotificationType.CUSTOM,
):
    notification = Notification.objects.create(
        registration=registration,
        channel=Notification.Channel.SMS,
        notification_type=notification_type,
        recipient=to,
        body=message,
        status=Notification.Status.PENDING,
    )

    backend_name = settings.SMS_BACKEND
    backend = BACKENDS.get(backend_name, _send_console)

    try:
        response = backend(to=to, message=message)

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.provider_response = (
            response if isinstance(response, dict) else {"raw": str(response)}
        )
        notification.save(
            update_fields=[
                "status",
                "sent_at",
                "provider_response",
                "updated_at",
            ]
        )

    except Exception as exc:  # noqa: BLE001
        notification.status = Notification.Status.FAILED
        notification.error_message = str(exc)
        notification.save(
            update_fields=["status", "error_message", "updated_at"]
        )

    return notification
