from django.db import models

from apps.common.models import UUIDModel


class Organization(UUIDModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name
    

class OrganizationMembership(UUIDModel):

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Administrator"
        FINANCE = "FINANCE", "Finance"
        REGISTRATION = "REGISTRATION", "Registration Manager"
        EVENT_MANAGER = "EVENT_MANAGER", "Event Manager"
        VIEWER = "VIEWER", "Viewer"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    organization = models.ForeignKey(
        Organization,
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
                    "organization",
                ],
                name="unique_user_organization_membership",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.organization.name} - "
            f"{self.role}"
        )