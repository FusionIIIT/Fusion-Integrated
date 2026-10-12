from celery import shared_task


@shared_task(name="elm.leave.year_end_process")
def year_end_process() -> str:
    return "ok"
