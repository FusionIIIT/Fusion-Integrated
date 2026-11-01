from celery import shared_task


@shared_task(name="visitors_hostel.generate_stay_alerts")
def generate_stay_alerts():
    from modules.visitors_hostel.services.alerts import generate_stay_alerts as run
    return run()


@shared_task(name="visitors_hostel.deliver_notifications")
def deliver_notifications():
    from modules.visitors_hostel.services.notifications import deliver_pending
    return deliver_pending()
