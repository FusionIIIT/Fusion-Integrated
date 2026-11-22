import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from kombu.exceptions import OperationalError

from modules.lms.domain import rules
from modules.lms.domain.state_machine import CONTENT_TRANSITIONS, transition
from modules.lms.models import Assignment, Material
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules, faculty

log = logging.getLogger("fusion.lms.release")


def _queue(kind, pk, at):
    from modules.lms.tasks import release_content

    try:
        release_content.apply_async(args=(kind, pk), eta=at)
    except OperationalError:
        # The bounded beat sweep recovers a missed ETA dispatch.
        log.warning("lms.release.dispatch_failed kind=%s id=%s", kind, pk)


@enforce_rules
@transaction.atomic
def change_release(scope, kind, pk, *, release_at=None, withdraw=False):
    faculty(scope)
    query = scoping.materials(scope) if kind == "material" else scoping.assignments(scope)
    row = get_object_or_404(query.select_for_update(of=("self",)), pk=pk)
    now = timezone.now()
    event = "withdraw" if withdraw else "schedule" if release_at is not None else "publish"
    state = transition(
        CONTENT_TRANSITIONS, row.state, event, scope.role, now=now, release_at=release_at
    )
    if kind == "assignment":
        rules.assignment(row.instructions, row.due_at, row.submission_type, row.points_possible)
        row.publisher_user_id = scope.user_id
    else:
        rules.payload(row.kind, row.text, row.url, bool(row.stored_file_id), material=True)
    row.state = ("PUBLISHED" if kind == "material" else "AVAILABLE") if state == "LIVE" else state
    row.release_at = release_at
    row.published_at = now if state == "LIVE" else None
    row.save()
    if state == "SCHEDULED":
        transaction.on_commit(lambda: _queue(kind, row.pk, release_at))
    return row


@enforce_rules
@transaction.atomic
def release_one(kind, pk):
    if kind not in ("material", "assignment"):
        raise ValueError("Unknown release kind")
    model = Material if kind == "material" else Assignment
    row = model.objects.select_for_update().filter(pk=pk).first()
    now = timezone.now()
    if row is None or row.state != "SCHEDULED" or row.release_at is None or row.release_at > now:
        return False
    transition(
        CONTENT_TRANSITIONS, row.state, "release", "SYSTEM", now=now, release_at=row.release_at
    )
    if kind == "assignment":
        rules.assignment(row.instructions, row.due_at, row.submission_type, row.points_possible)
    else:
        rules.payload(row.kind, row.text, row.url, bool(row.stored_file_id), material=True)
    row.state = "PUBLISHED" if kind == "material" else "AVAILABLE"
    row.published_at = now
    row.save()
    log.info("lms.release.completed kind=%s id=%s", kind, pk)
    return True
