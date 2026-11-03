from celery import shared_task


@shared_task(name="pms.process_deadlines", acks_late=True, reject_on_worker_lost=True)
def process_deadlines():
    from modules.pms.services.deadlines import process_deadlines as process

    return process()


@shared_task(name="pms.scan_documents", acks_late=True, reject_on_worker_lost=True)
def scan_documents(limit=100):
    from modules.pms.services.scanning import scan_pending_documents

    return scan_pending_documents(limit=limit)


@shared_task(name="pms.deliver_notifications", acks_late=True, reject_on_worker_lost=True)
def deliver_notifications(limit=250):
    from modules.pms.services.notifications import deliver_pending

    return deliver_pending(limit=limit)
