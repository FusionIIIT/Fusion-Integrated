from celery import shared_task


@shared_task(
    name="employee_leave.process_sla",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=240,
    time_limit=300,
)
def process_sla() -> dict[str, int]:
    from modules.employee_leave.services import process_sla as run_sla

    return run_sla()
