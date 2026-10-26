from celery import shared_task


@shared_task(name="leave.process_sla")
def process_leave_sla():
    from modules.leave.services import process_sla

    return process_sla()
