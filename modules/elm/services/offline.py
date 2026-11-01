from datetime import date
from decimal import Decimal
from django.db import transaction
from modules.elm.domain.counting import chargeable_days
from modules.elm.domain.policy import PolicyViolation
from modules.elm.domain.state_machine import transition as require_transition
from modules.elm.models import LeaveAccountLock, LeaveRequest, LeaveTransition, OfflineLeaveRecord
from modules.directory import contracts as directory
from modules.elm.services import ledger

@transaction.atomic
def record(*, user_id: int, category: str, start_date: date, end_date: date, recorded_by_user_id: int,
           sanction_reference: str = "", evidence: list | None = None, note: str = "", days: Decimal | None = None) -> OfflineLeaveRecord:
    if end_date < start_date:
        raise PolicyViolation("invalid_dates", "End date must not be before start date.")
    if not (sanction_reference.strip() or evidence):
        raise PolicyViolation("sanction_evidence_required", "An offline sanction reference or supporting evidence is required.")
    LeaveAccountLock.objects.get_or_create(user_id=user_id)
    LeaveAccountLock.objects.select_for_update().get(user_id=user_id)
    employee = directory.get_users([user_id]).get(user_id)
    if not employee or not employee.is_active or employee.kind not in {"faculty", "staff"}:
        raise PolicyViolation("employee_not_found", "Offline leave must belong to an active institute employee.")
    if OfflineLeaveRecord.objects.filter(user_id=user_id, category=category, start_date=start_date, end_date=end_date).exists():
        raise PolicyViolation("duplicate_offline_record", "This offline leave record already exists.")
    count = days if days is not None else chargeable_days(category, start_date, end_date)
    if count <= 0:
        raise PolicyViolation("invalid_days", "Offline leave must have a positive chargeable duration.")
    require_transition("", "offline_record_sync", "leave_administrator")
    req = LeaveRequest.objects.create(user_id=user_id, category=category, start_date=start_date, end_date=end_date,
        days=count, status="approved", current_role="", submitted_at=None, decided_at=None,
        purpose=f"Offline sanctioned leave: {sanction_reference}".strip(), evidence=evidence or [])
    LeaveTransition.objects.create(request=req, from_status="", to_status="approved", event="offline_record_sync", actor_user_id=recorded_by_user_id, note=note, data={"sanction_reference": sanction_reference})
    ledger.ensure_annual_credits(user_id, start_date.year, kind=employee.kind)
    ledger.post_request_debit(req)
    return OfflineLeaveRecord.objects.create(user_id=user_id, category=category, start_date=start_date, end_date=end_date,
        days=count, sanction_reference=sanction_reference, evidence=evidence or [], recorded_by_user_id=recorded_by_user_id,
        note=note, synced_request=req)
