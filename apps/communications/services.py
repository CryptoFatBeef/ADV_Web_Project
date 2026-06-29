from django.template import Context, Template
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def render_body(template_str: str, context: dict) -> str:
    """Render a Django template string with given context dict."""
    return Template(template_str).render(Context(context))


def send_notification(notification):
    """
    Dispatch a single Notification instance.
    Mutates status, sent_at, and failure_reason in place.
    Caller must call notification.save() after this function.
    """
    try:
        if notification.channel == 'IN_APP':
            notification.status = 'SENT'
            notification.sent_at = timezone.now()

        elif notification.channel == 'EMAIL':
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[notification.recipient.user.email],
                fail_silently=False,
            )
            notification.status = 'SENT'
            notification.sent_at = timezone.now()

        elif notification.channel == 'WHATSAPP':
            # Phase 1 stub — Meta Cloud API / Twilio not yet configured
            notification.status = 'FAILED'
            notification.failure_reason = 'WhatsApp dispatch not yet implemented.'

    except Exception as e:
        notification.status = 'FAILED'
        notification.failure_reason = str(e)[:500]
