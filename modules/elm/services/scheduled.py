"""Scheduled processing: year-end (SF-EL-001, WF-EL-07) and SLA (SF-EL-002, WF-EL-08)."""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.directory.contracts import get_employees
from modules.elm.models import LeaveAccount, LeaveTransaction, SlaLog, WorkflowTask
from modules.elm.services import accounts, applications, policy, routing

T = LeaveTransaction.Kind
LAPSE_TYPES = ("CL", "RH", "SCL")          # BR-EL-002..004: no carry-forward
CARRY_TYPES = ("EL", "COL")                # BR-EL-005, 008, 009: carried forward
CENT = Decimal("0.01")


def _close_user(user_id: int, year: int, ratio: Decimal, summary: dict) -> None:
    for acct in LeaveAccount.objects.filter(user_id=user_id, year=year):
        bal = acct.balance
        if bal <= 0:
            continue
        kind = acct.leave_type
        if kind in LAPSE_TYPES:
            accounts.post(user_id, year, kind, T.LAPSE, -bal, note=f"Year-end lapse {year}")
            summary["lapsed"] += 1
        elif kind == "VL":
            # BR-EL-007/008: all unused VL converts at 2:1, fractions allowed; VL never carries.
            el = (bal / ratio).quantize(CENT)
            accounts.post(user_id, year, "VL", T.CONVERT_OUT, -bal, note=f"VL converted {year}")
            accounts.post(user_id, year + 1, "EL", T.CONVERT_IN, el,
                          note=f"EL from VL conversion {year}")
            summary["converted"] += 1
        elif kind in CARRY_TYPES:
            accounts.post(user_id, year, kind, T.CARRY_FORWARD, -bal,
                          note=f"Carried to {year + 1}")
            accounts.post(user_id, year + 1, kind, T.CARRY_FORWARD, bal,
                          note=f"Carried from {year}")
            summary["carried"] += 1


def process_year_end(year: int) -> dict:
    """Lapse CL/RH/SCL, convert faculty VL to EL, carry EL/COL forward, report exceptions.
    Safe to re-run: closed accounts have zero balance, so nothing is posted twice.
    One person's failure is reported and never blocks everyone else."""
    params = policy.get_effective_policy().params          # precondition: a policy is in force
    ratio = Decimal(str(params.get("VL_PER_EL", 2)))
    summary = {"year": year, "lapsed": 0, "converted": 0, "carried": 0, "exceptions": []}
    user_ids = sorted(set(LeaveAccount.objects.filter(year=year).values_list("user_id", flat=True)))
    for uid in user_ids:
        try:
            with transaction.atomic():
                _close_user(uid, year, ratio, summary)
        except Exception as exc:  # noqa: BLE001 - reported in the summary, never swallowed
            summary["exceptions"].append({"user_id": uid, "error": str(exc)})
    return summary


def credit_year(year: int) -> int:
    """Annual entitlement for every employee (BR-EL-002..009). Idempotent."""
    params = policy.get_effective_policy().params
    count = 0
    for emp in get_employees():
        count += len(accounts.credit_annual(emp.user_id, year, emp.kind, params))
    return count


# ---- SLA -----------------------------------------------------------------

DEFAULT_REMINDER_HOURS = 48
DEFAULT_ESCALATION_HOURS = 96


def _sla_hours() -> tuple[int, int]:
    try:
        params = policy.get_effective_policy().params
    except policy.NoPublishedPolicy:
        params = {}
    return (params.get("SLA_REMINDER_HOURS", DEFAULT_REMINDER_HOURS),
            params.get("SLA_ESCALATION_HOURS", DEFAULT_ESCALATION_HOURS))


def _escalation_target(task: WorkflowTask) -> int | None:
    """The configured higher authority: the final authority, or the Director rule
    when the task already sits with the final authority."""
    req = task.request
    try:
        prof = applications._profile(req.applicant_id)
    except applications.ApplicationError:
        return None
    who = {"applicant_id": req.applicant_id, "unit": prof.department, "kind": prof.kind,
               "leave_type": req.leave_type}
    for stage in (routing.Stage.FINAL, routing.Stage.DIRECTOR):
        try:
            target = routing.approver_for(stage, **who)
        except routing.RoutingError:
            continue
        if target != task.assignee_id:
            return target
    return None


def process_sla(now=None) -> dict:
    """Only tasks still open get a reminder or escalation (SRS-EL-107). Each is logged once."""
    now = now or timezone.now()
    reminder_h, escalation_h = _sla_hours()
    summary = {"reminders": 0, "escalations": 0}
    open_tasks = WorkflowTask.objects.filter(
        status=WorkflowTask.Status.OPEN).select_related("request")
    for task in open_tasks:
        age = now - task.created_at
        if age >= timedelta(hours=reminder_h):
            _, made = SlaLog.objects.get_or_create(
                task=task, action=SlaLog.Action.REMINDER,
                defaults={"notified_id": task.assignee_id})
            summary["reminders"] += int(made)
        if age >= timedelta(hours=escalation_h):
            _, made = SlaLog.objects.get_or_create(
                task=task, action=SlaLog.Action.ESCALATION,
                defaults={"notified_id": _escalation_target(task)})
            summary["escalations"] += int(made)
    return summary
