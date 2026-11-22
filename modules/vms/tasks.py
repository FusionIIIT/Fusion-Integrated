from celery import shared_task


@shared_task(name="vms.expire_overdue_visits", acks_late=True, reject_on_worker_lost=True)
def expire_overdue_visits():
    from modules.vms.services.scheduled import expire_overdue

    return expire_overdue()


@shared_task(name="vms.expire_visit_passes", acks_late=True, reject_on_worker_lost=True)
def expire_visit_passes():
    from modules.vms.services.scheduled import expire_passes

    return expire_passes()


@shared_task(name="vms.auto_checkout_visitors", acks_late=True, reject_on_worker_lost=True)
def auto_checkout_visitors():
    from modules.vms.services.scheduled import expire_on_site_visits

    return expire_on_site_visits()


@shared_task(name="vms.deliver_notifications", acks_late=True, reject_on_worker_lost=True)
def deliver_notifications():
    from modules.vms.services.scheduled import send_pending

    return send_pending()


@shared_task(name="vms.reconcile_offline_entries", acks_late=True, reject_on_worker_lost=True)
def reconcile_offline_entries():
    from modules.vms.services.visits import reconcile_offline_entries as reconcile

    return reconcile()


@shared_task(name="vms.queue_approval_reminders", acks_late=True, reject_on_worker_lost=True)
def queue_approval_reminders():
    from modules.vms.services.scheduled import queue_approval_reminders as queue

    return queue()


@shared_task(
    name="vms.scan_visitor_document",
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def scan_visitor_document(document_id):
    from django.utils import timezone

    from modules.vms.models import VisitorDocument
    from modules.vms.services.document_storage import scan_with_clamav

    document = VisitorDocument.objects.filter(pk=document_id, scan_status="pending").first()
    if document is None:
        return "already_processed"
    try:
        result, detail = scan_with_clamav(document.storage_key)
    except (OSError, RuntimeError):
        if scan_visitor_document.request.retries >= 5:
            VisitorDocument.objects.filter(pk=document_id, scan_status="pending").update(
                scan_status="failed",
                scan_detail="Malware scanner unavailable",
                scanned_at=timezone.now(),
            )
        raise
    VisitorDocument.objects.filter(pk=document_id, scan_status="pending").update(
        scan_status=result, scan_detail=detail, scanned_at=timezone.now()
    )
    return result


@shared_task(name="vms.scan_pending_documents", acks_late=True, reject_on_worker_lost=True)
def scan_pending_documents():
    from modules.vms.models import VisitorDocument

    ids = list(
        VisitorDocument.objects.filter(scan_status="pending")
        .order_by("uploaded_at")
        .values_list("pk", flat=True)[:100]
    )
    for document_id in ids:
        scan_visitor_document.delay(document_id)
    return len(ids)
