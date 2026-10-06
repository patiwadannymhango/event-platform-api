"""
Email sending, using Django's built-in SMTP backend configured in
settings (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD — Gmail App Password).

Every send is logged to the Notification model regardless of success or
failure, so the admin can see delivery status per registration.
"""

from email.mime.image import MIMEImage

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Notification


def send_email(
    *,
    to,
    subject,
    text_body,
    html_body=None,
    registration=None,
    notification_type=Notification.NotificationType.CUSTOM,
    inline_images=None,
):
    """
    inline_images: optional list of (content_id, file_path) pairs to embed
    directly in the message (MIME multipart/related) rather than link to.
    An <img src="cid:{content_id}"> in html_body then renders from the
    attachment itself — no external fetch, so it isn't affected by a mail
    client's "don't auto-load remote images" default (the usual reason a
    hosted-URL logo silently fails to show in Outlook) and isn't subject
    to the sending domain's reputation either.
    """
    notification = Notification.objects.create(
        registration=registration,
        channel=Notification.Channel.EMAIL,
        notification_type=notification_type,
        recipient=to,
        subject=subject,
        body=text_body,
        status=Notification.Status.PENDING,
    )

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            to=[to],
        )

        if html_body:
            message.attach_alternative(html_body, "text/html")

        if inline_images:
            message.mixed_subtype = "related"
            for content_id, file_path in inline_images:
                with open(file_path, "rb") as f:
                    image = MIMEImage(f.read())
                image.add_header("Content-ID", f"<{content_id}>")
                image.add_header("Content-Disposition", "inline", filename=file_path.split("/")[-1])
                message.attach(image)

        message.send(fail_silently=False)

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save(
            update_fields=["status", "sent_at", "updated_at"]
        )

    except Exception as exc:  # noqa: BLE001 — we want to log any failure
        notification.status = Notification.Status.FAILED
        notification.error_message = str(exc)
        notification.save(
            update_fields=["status", "error_message", "updated_at"]
        )

    return notification
