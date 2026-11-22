import logging

from celery import shared_task
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.lms.models import Assignment, Material
from modules.lms.services.releases import release_one

log = logging.getLogger("fusion.lms.release")


@shared_task(acks_late=True)
def release_content(kind, pk):
    try:
        return release_one(kind, pk)
    except DomainError:
        log.exception("lms.release.validation_failed kind=%s id=%s", kind, pk)
        return False


def _sweep(kind, model):
    ids = list(
        model.objects.filter(state="SCHEDULED", release_at__lte=timezone.now())
        .order_by("release_at", "pk")
        .values_list("pk", flat=True)[:50]
    )
    return sum(release_content(kind, pk) for pk in ids)


@shared_task(acks_late=True)
def release_due_materials():
    return _sweep("material", Material)


@shared_task(acks_late=True)
def release_due_assignments():
    return _sweep("assignment", Assignment)
