from django.db import models

from apps.common.models import UUIDModel
from apps.organizations.models import Organization


class Event(UUIDModel):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        ARCHIVED = "ARCHIVED", "Archived"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="events",
    )

    payment_account = models.ForeignKey(
        "payments.PaymentAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="events",
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    start_date = models.DateTimeField()

    end_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_event_slug_per_organization",
            )
        ]

    def __str__(self):
        return self.name
    

class EventMembership(UUIDModel):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Event Administrator"
        FINANCE = "FINANCE", "Finance"
        REGISTRATION = "REGISTRATION", "Registration Manager"
        VIEWER = "VIEWER", "Viewer"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="event_memberships",
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "event",
                ],
                name="unique_user_event_membership",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.event.name} - "
            f"{self.role}"
        )