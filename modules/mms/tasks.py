"""MMS event processing; scheduled transitions are idempotent and recoverable."""
import logging

from celery import shared_task
from django.conf import settings

log = logging.getLogger("fusion.mms.tasks")


@shared_task(name="mms.process_deadlines", acks_late=True, reject_on_worker_lost=True)
def process_deadlines() -> dict[str, int]:
    from modules.mms.services import operations

    expired_roles = operations.expire_role_assignments()
    deregistrations = operations.activate_deregistrations()
    vacation_defaults = operations.default_vacation_responses()
    if settings.MMS_SPECIAL_FOOD_DECISION_HOURS is None:
        log.error("mms.special_food.timeout_disabled institution decision period is unset")
        special_food_rejections = 0
    else:
        special_food_rejections = operations.reject_expired_special_food(
            decision_hours=settings.MMS_SPECIAL_FOOD_DECISION_HOURS)
    return {
        "expired_roles": expired_roles,
        "deregistrations": deregistrations,
        "vacation_defaults": vacation_defaults,
        "special_food_rejections": special_food_rejections,
    }


@shared_task(name="mms.deliver_notifications", acks_late=True,
             reject_on_worker_lost=True)
def deliver_notifications(limit: int | None = None) -> str:
    from modules.mms.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("mms.notify.run %s", report)
    return str(report)


@shared_task(name="mms.generate_ready_bills", acks_late=True,
             reject_on_worker_lost=True)
def generate_ready_bills() -> int:
    from modules.mms.services import operations

    count = operations.generate_ready_bills()
    if count:
        log.info("mms.bills.generated count=%d", count)
    return count
