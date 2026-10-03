from celery import shared_task


# Gmail's SMTP (what EMAIL_HOST_USER/PASSWORD in settings point at) will
# throttle or flag an account that sends too fast — this isn't a
# transactional confirmation, it's a one-off broadcast to a thousand-plus
# people, so the worker is deliberately rate-limited rather than firing
# everything the moment it's queued. autoretry handles the transient SMTP
# hiccups (a dropped connection, a momentary Gmail 4xx) that are routine
# at this volume.
@shared_task(
    rate_limit="20/m",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def send_race_pack_email(registration_id):
    from apps.notifications.email import send_email
    from apps.notifications.models import Notification
    from apps.notifications.race_pack_email import build_race_pack_email
    from apps.registrations.models import Registration

    try:
        registration = Registration.objects.select_related("participant").get(id=registration_id)
    except Registration.DoesNotExist:
        return "registration no longer exists"

    # Closes the race between "admin clicks Send twice" and "the queue
    # hasn't drained yet" — the enqueueing view already filters out
    # anyone already sent, but that's a point-in-time check; this is the
    # one that actually prevents a duplicate send.
    already_sent = Notification.objects.filter(
        registration=registration,
        notification_type=Notification.NotificationType.RACE_PACK_COLLECTION,
        status=Notification.Status.SENT,
    ).exists()
    if already_sent:
        return "already sent"

    email = registration.participant.email
    if not email:
        return "no email on file"

    subject, text_body, html_body = build_race_pack_email(
        first_name=registration.participant.first_name or "Runner",
        reference=registration.registration_number,
    )

    send_email(
        to=email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        registration=registration,
        notification_type=Notification.NotificationType.RACE_PACK_COLLECTION,
    )
    return "sent"
