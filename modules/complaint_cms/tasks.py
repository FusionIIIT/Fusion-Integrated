from celery import shared_task

@shared_task
def cms_process_sla():
    from .services.events import process_complaint_sla
    process_complaint_sla()

@shared_task
def cms_auto_close_resolved():
    from .services.events import auto_close_resolved_complaints
    auto_close_resolved_complaints()