"""Idempotent scheduled year-end and pending-only SLA operations."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.elm.domain.state_machine import CREDITS, PENDING
from modules.elm.models import EmployeeRecord, LeaveRequest

from .leave_service import account, entry, log, notify, policy


def require_consistency(condition, message):
    if not condition:
        raise ConflictError(message)


def close_year(year):
    if year >= timezone.localdate().year:
        raise DomainError("The year-end boundary has not been reached.")
    report = {"processed": [], "exceptions": []}
    for user_id in EmployeeRecord.objects.filter(is_active=True).values_list("user_id", flat=True):
        try:
            with transaction.atomic():
                profile = EmployeeRecord.objects.select_for_update().get(user_id=user_id)
                balances = {c: account(profile, c, year) for c in CREDITS}
                if all(b.closed for b in balances.values()):
                    continue
                if (
                    LeaveRequest.objects.filter(
                        applicant_user_id=user_id, start_date__year=year, status__in=PENDING
                    ).exists()
                    or any(b.closed for b in balances.values())
                    or any(b.pending for b in balances.values())
                ):
                    require_consistency(
                        False, "Reconcile partially closed accounts or pending leave first."
                    )
                carry = {"EL": balances["EL"].balance, "COL": balances["COL"].balance}
                if profile.kind == "faculty":
                    carry["EL"] += balances["VL"].balance / Decimal(2)
                for category, amount in carry.items():
                    target = account(profile, category, year + 1)
                    if target.closed or amount < 0:
                        require_consistency(False, "Invalid carry-forward account.")
                    target.credited += amount
                    target.save(update_fields=["credited"])
                    entry(target, "CARRY_FORWARD", amount, "system")
                for category, balance in balances.items():
                    action = (
                        "VL_TO_EL"
                        if category == "VL" and profile.kind == "faculty"
                        else "YEAR_END_CLOSE"
                    )
                    entry(balance, action, balance.balance, "system")
                    balance.closed = True
                    balance.save(update_fields=["closed"])
                report["processed"].append(user_id)
        except (ConflictError, DomainError) as exc:
            report["exceptions"].append({"user_id": user_id, "error": str(exc)})
    return report


def process_sla():
    p, now = policy(), timezone.now()
    result = {"reminders": 0, "escalations": 0}
    for pk in LeaveRequest.objects.filter(status__in=PENDING).values_list("pk", flat=True):
        with transaction.atomic():
            req = LeaveRequest.objects.select_for_update().get(pk=pk)
            if req.status not in PENDING:
                continue
            elapsed = (now - req.task_assigned_at).total_seconds() / 3600
            if elapsed >= p.reminder_hours and not req.reminder_sent:
                notify(req, req.current_approver_user_id, "SLA_REMINDER")
                log(req, "system", "SLA_REMINDER", role="system")
                req.reminder_sent = True
                result["reminders"] += 1
            if elapsed >= p.escalation_hours and not req.escalation_sent:
                profile = EmployeeRecord.objects.get(user_id=req.applicant_user_id)
                recipient = profile.escalation_user_id or req.current_approver_user_id
                notify(req, recipient, "SLA_ESCALATION")
                log(req, "system", "SLA_ESCALATION", role="system")
                req.escalation_sent = True
                result["escalations"] += 1
            req.save(update_fields=["reminder_sent", "escalation_sent"])
    return result
