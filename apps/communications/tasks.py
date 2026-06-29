from celery import shared_task


@shared_task
def dispatch_pending_notifications():
    """Process all PENDING notifications in the queue."""
    from apps.communications.models import Notification
    from apps.communications.services import send_notification

    pending = Notification.objects.filter(status='PENDING').select_related(
        'recipient__user', 'template'
    )
    sent, failed = 0, 0
    for n in pending:
        send_notification(n)
        n.save(update_fields=['status', 'sent_at', 'failure_reason'])
        if n.status == 'SENT':
            sent += 1
        else:
            failed += 1
    return f'Dispatched: {sent} sent, {failed} failed.'
