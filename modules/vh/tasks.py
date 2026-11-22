# Celery background tasks for vh stay monitoring and notifications.
from celery import shared_task


@shared_task(name="vh.evaluate_no_shows")
def evaluate_no_shows() -> int:
    # Evaluates no-shows for bookings where expected arrival passed.
    from modules.vh.services.alerts import evaluate_no_shows as run_evaluation

    return run_evaluation()


@shared_task(name="vh.evaluate_overstays")
def evaluate_overstays() -> int:
    # Evaluates overstays for guests whose departure passed.
    from modules.vh.services.alerts import evaluate_overstays as run_evaluation

    return run_evaluation()


@shared_task(name="vh.send_stay_reminders")
def send_stay_reminders() -> int:
    # Dispatches check-in and check-out reminder notifications.
    from modules.vh.services.notifications import dispatch_scheduled_stay_reminders

    return dispatch_scheduled_stay_reminders()


@shared_task(name="vh.check_inventory_thresholds")
def check_inventory_thresholds() -> int:
    # Checks inventory quantities against thresholds and triggers alerts.
    from modules.vh.services.inventory import evaluate_all_inventory_thresholds

    return evaluate_all_inventory_thresholds()
