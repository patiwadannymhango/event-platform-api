from django.db import models

from apps.common.models import UUIDModel


class Notification(UUIDModel):
    """
    A log of every email/SMS the platform has attempted to send. This is
    what the admin's "notifications" view reads from — it's the audit
    trail for "did the runner actually get their confirmation".
    """

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    class NotificationType(models.TextChoices):
        REGISTRATION_RECEIVED = (
            "REGISTRATION_RECEIVED",
            "Registration received",
        )
        RESERVATION_CONFIRMED = (
            "RESERVATION_CONFIRMED",
            "Reservation confirmed",
        )
        PAYMENT_CONFIRMED = (
            "PAYMENT_CONFIRMED",
            "Payment confirmed",
        )
        PAYMENT_FAILED = (
            "PAYMENT_FAILED",
            "Payment failed",
        )
        REFUND_PROCESSED = (
            "REFUND_PROCESSED",
            "Refund processed",
        )
        CUSTOM = "CUSTOM", "Custom"

    registration = models.ForeignKey(
        "registrations.Registration",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
    )

    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.CUSTOM,
    )

    recipient = models.CharField(
        max_length=255,
        help_text="Email address or phone number the message was sent to.",
    )

    subject = models.CharField(
        max_length=255,
        blank=True,
    )

    body = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    error_message = models.TextField(
        blank=True,
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"{self.channel} to {self.recipient} ({self.status})"
