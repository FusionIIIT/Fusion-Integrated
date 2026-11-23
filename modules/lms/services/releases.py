import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from kombu.exceptions import OperationalError

from modules.lms.domain import rules
from modules.lms.domain.state_machine import CONTENT_TRANSITIONS, transition
from modules.lms.models import Assignment, ContentTransitionLog, Material
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules, faculty

log = logging.getLogger("fusion.lms.release")


def _queue(kind, pk, at):
    from modules.lms.tasks import release_content

    try:
        release_content.apply_async(args=(kind, pk), eta=at)
    except OperationalError:
        log.warning("lms.release.dispatch_failed kind=%s id=%s", kind, pk)


def _query(kind, scope):
    if kind not in ("material", "assignment"):
        raise ValueError("Unknown release kind")
    if scope is None:
        return (Material if kind == "material" else Assignment).objects.all()
    faculty(scope)
    return scoping.materials(scope) if kind == "material" else scoping.assignments(scope)


def _validate(row, kind):
    if kind == "assignment":
        rules.assignment(row.instructions, row.due_at, row.submission_type, row.points_possible)
    else:
        rules.payload(row.kind, row.text, row.url, bool(row.stored_file_id), material=True)


@enforce_rules
@transaction.atomic
def transition_content(kind, pk, event, *, scope=None, release_at=None):
    query = _query(kind, scope).select_for_update(of=("self",))
    row = query.filter(pk=pk).first() if scope is None else get_object_or_404(query, pk=pk)
    now = timezone.now()
    if scope is None:
        if event != "release":
            rules.require_role("SYSTEM", ("FACULTY",))
        if (
            row is None
            or row.state != "SCHEDULED"
            or row.release_at is None
            or row.release_at > now
        ):
            return False
        release_at = row.release_at
    role = scope.role if scope else "SYSTEM"
    target = transition(CONTENT_TRANSITIONS, row.state, event, role, now=now, release_at=release_at)
    _validate(row, kind)
    old_state, old_at = row.state, row.release_at
    row.state = ("PUBLISHED" if kind == "material" else "AVAILABLE") if target == "LIVE" else target
    row.release_at = release_at
    row.published_at = now if target == "LIVE" else None
    if kind == "assignment" and scope is not None:
        row.publisher_user_id = scope.user_id
    row.save()
    ContentTransitionLog.objects.create(
        **{kind: row},
        actor_user_id=scope.user_id if scope else None,
        actor_role=role,
        event=event,
        old_state=old_state,
        new_state=row.state,
        old_release_at=old_at,
        new_release_at=row.release_at,
        changed_at=now,
    )
    if target == "SCHEDULED":
        transaction.on_commit(lambda: _queue(kind, row.pk, release_at))
    log.info("lms.release.transition kind=%s id=%s event=%s", kind, pk, event)
    return row if scope is not None else True


def change_release(scope, kind, pk, *, release_at=None, withdraw=False):
    event = "withdraw" if withdraw else "schedule" if release_at is not None else "publish"
    return transition_content(kind, pk, event, scope=scope, release_at=release_at)


def release_one(kind, pk):
    return transition_content(kind, pk, "release")
