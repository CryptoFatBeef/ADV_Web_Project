from celery import shared_task


@shared_task
def reconcile_fps_payments():
    """
    Stub: query PaymentRecords in SCREENSHOT_UPLOADED state and return a count.
    Real IMAP reconciliation deferred — track processed email UIDs on implementation
    to prevent double-reconciliation on retry.
    """
    from apps.payments.models import PaymentRecord, PaymentStatus

    pending = PaymentRecord.objects.filter(status=PaymentStatus.SCREENSHOT_UPLOADED)
    return f'{pending.count()} FPS payment(s) pending reconciliation'
