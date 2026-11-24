"""HOD and Dept_Admin tenures (UC-DEPT-020) and their taking effect (UC-DEPT-022), per Q1."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.department.domain import rules
from modules.department.domain.roles import CENTRAL, ActorContext
from modules.department.models import Department, RoleTenure
from modules.department.selectors import scoping
from modules.department.services import notifications
from modules.department.services.common import get_scoped, require_acting, translated
from modules.directory import contracts as directory

#: How far in the past a tenure may start, so a clock skew is not a refusal but a back-date is.
BACKDATE_GRACE = timedelta(minutes=5)


def _as_tenure(t: RoleTenure) -> rules.Tenure:
    return rules.Tenure(key=t.pk, user_id=t.user_id, valid_from=t.valid_from, valid_to=t.valid_to)


def _check_dates_and_holder(user_id: int, valid_from, valid_to, now) -> None:
    """BR-DEPT-023 dates, no back-dating, and AFR-DEPT-047 employees only."""
    with translated():
        rules.validate_interval(valid_from, valid_to)
    if valid_from < now - BACKDATE_GRACE:
        raise DomainError(
            "A tenure cannot start in the past; record it from now or later.",
            code="backdated_tenure",
        )
    user = directory.get_users([user_id]).get(user_id)
    if user is None or user.kind not in rules.EMPLOYEE_KINDS:
        raise DomainError(
            "Only an institute employee (faculty or staff) can hold this role.", code="not_employee"
        )


def _locked_department(code: str) -> Department:
    dept = Department.objects.select_for_update().filter(code=code).first()
    if dept is None:
        raise NotFoundError(f"There is no department {code}. Choose one of the listed departments.")
    return dept


def _refuse_gap(dept: Department, role: str, valid_from, now) -> None:
    """BR-DEPT-022: a recorded holder runs until the latest end, so a later start leaves a gap."""
    latest_end = (
        RoleTenure.objects.filter(department=dept, role=role, valid_to__gt=now)
        .order_by("-valid_to")
        .values_list("valid_to", flat=True)
        .first()
    )
    if latest_end is not None and valid_from > latest_end:
        raise DomainError(
            f"The current {rules.ROLE_LABELS[role]} tenure ends on "
            f"{timezone.localtime(latest_end):%Y-%m-%d %H:%M}. "
            "Start the new tenure then or earlier, so the role is never left empty.",
            code="would_leave_gap",
        )


def _hand_over(dept: Department, role: str, candidate: rules.Tenure) -> None:
    """End the outgoing tenure at the new start, then refuse any overlap that is left."""
    existing = list(
        RoleTenure.objects.filter(department=dept, role=role, valid_to__gt=candidate.valid_from)
    )
    outgoing = [t for t in existing if t.valid_from < candidate.valid_from < t.valid_to]
    for t in outgoing:
        if candidate.valid_to < t.valid_to:
            # BR-DEPT-022 (R5-01): cutting the incumbent short would leave the rest of it empty.
            raise DomainError(
                f"The current {rules.ROLE_LABELS[role]} tenure runs until "
                f"{timezone.localtime(t.valid_to):%Y-%m-%d %H:%M}. End the new tenure then or "
                "later, or shorten the current tenure first, so the role is never left empty.",
                code="would_cut_short",
            )
        t.valid_to = candidate.valid_from
        t.save(update_fields=["valid_to", "updated_at"])
    remaining = [_as_tenure(t) for t in existing if t not in outgoing]
    if rules.overlapping(candidate, remaining):
        raise ConflictError(
            "Another tenure for this role overlaps those dates; change it first.",
            code="tenure_overlap",
        )


@transaction.atomic
def assign(
    ctx: ActorContext,
    *,
    department_code: str,
    role: str,
    user_id: int,
    valid_from,
    valid_to,
    now=None,
) -> RoleTenure:
    """BR-DEPT-021 by permission, BR-DEPT-022/023 dates, AFR-DEPT-047 employees only."""
    require_acting(ctx, CENTRAL)
    now = now or timezone.now()
    if role not in rules.ASSIGNABLE_ROLES:
        raise DomainError("Choose the role hod or dept_admin and try again.", code="invalid_role")
    dept = _locked_department(department_code)
    _check_dates_and_holder(user_id, valid_from, valid_to, now)
    _refuse_gap(dept, role, valid_from, now)
    candidate = rules.Tenure(key=None, user_id=user_id, valid_from=valid_from, valid_to=valid_to)
    _hand_over(dept, role, candidate)
    return RoleTenure.objects.create(
        department=dept,
        role=role,
        user_id=user_id,
        valid_from=valid_from,
        valid_to=valid_to,
        assigned_by=ctx.user_id,
    )


@transaction.atomic
def change(ctx: ActorContext, tenure_id: int, *, valid_to, now=None) -> RoleTenure:
    """UC-DEPT-020 "change": move the end date, never opening a gap or an overlap."""
    require_acting(ctx, CENTRAL)
    now = now or timezone.now()
    tenure = get_scoped(scoping.tenures_for(ctx), tenure_id, lock=True, what="tenure")
    Department.objects.select_for_update().get(pk=tenure.department_id)
    others = [
        _as_tenure(t)
        for t in RoleTenure.objects.filter(
            department_id=tenure.department_id, role=tenure.role
        ).exclude(pk=tenure.pk)
    ]
    if tenure.valid_to <= now:
        raise ConflictError(
            "This tenure has already ended. Record a new tenure instead of changing it.",
            code="tenure_ended",
        )
    with translated():
        rules.validate_interval(tenure.valid_from, valid_to)
        rules.check_shortening(
            current=_as_tenure(tenure), new_valid_to=valid_to, successors=others, now=now
        )
    if valid_to < now:
        raise DomainError(
            "Choose an end date from now onwards; a tenure cannot end in the past.",
            code="backdated_tenure",
        )
    moved = rules.Tenure(
        key=tenure.pk, user_id=tenure.user_id, valid_from=tenure.valid_from, valid_to=valid_to
    )
    if rules.overlapping(moved, others):
        raise ConflictError(
            "That end date would overlap the next holder's tenure.", code="tenure_overlap"
        )
    tenure.valid_to = valid_to
    tenure.save(update_fields=["valid_to", "updated_at"])
    return tenure


def apply_transitions(*, now=None) -> int:
    """UC-DEPT-022: stamp each tenure that has started, once, and tell the incoming holder."""
    now = now or timezone.now()
    applied = 0
    for pk in RoleTenure.objects.filter(
        transition_applied_at__isnull=True, valid_from__lte=now, valid_to__gt=now
    ).values_list("pk", flat=True):
        with transaction.atomic():
            won = RoleTenure.objects.filter(pk=pk, transition_applied_at__isnull=True).update(
                transition_applied_at=now
            )
            if not won:
                continue
            t = RoleTenure.objects.select_related("department").get(pk=pk)
            notifications.enqueue(
                topic="role.effective",
                key=str(t.pk),
                recipients=[t.user_id],
                subject=f"[{t.department.code}] Your {t.get_role_display()} tenure has started",
                body=f"Your tenure runs until {t.valid_to:%Y-%m-%d %H:%M}.",
            )
            applied += 1
    return applied
