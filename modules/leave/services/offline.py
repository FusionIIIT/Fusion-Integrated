"""Offline leave synchronization service.

Implements EL-UC-016, BR-EL-029, BR-EL-037.
Synchronizes authorized paper/offline leaves without initiating a second approval workflow.
"""

from datetime import date

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.directory.contracts import get_users
from modules.leave.domain.constants import Event, HalfDay, LedgerTransactionType, RequestStatus
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.exceptions import LeaveDomainError
from modules.leave.domain.validation import validate_category_eligibility
from modules.leave.models.ledger import LeaveLedgerEntry
from modules.leave.models.offline import OfflineLeaveRecord
from modules.leave.models.requests import LeaveAuditEvent, LeaveRequest
from modules.leave.selectors.calendar import get_closed_holidays
from modules.leave.services.transitions import _translate_error


def record_offline_sanctioned_leave(
    principal: Principal,
    employee_user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    sanction_reference_number: str,
    sanction_date: date,
    sanctioning_authority_name: str,
    offline_reason: str,
    half_day: str = HalfDay.NONE.value,
) -> LeaveRequest:
    """Retrospectively synchronizes offline-sanctioned leave (EL-UC-016 / BR-EL-029)."""
    users = get_users([employee_user_id])
    user_dto = users.get(employee_user_id)
    if not user_dto:
        raise BadRequestError(f"Employee user ID {employee_user_id} not found in directory.")

    employee_kind = user_dto.kind
    department = user_dto.department

    try:
        validate_category_eligibility(category, employee_kind)
        year = start_date.year
        closed_holidays = get_closed_holidays(year)
        days_count = calculate_leave_days(
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            closed_holidays=closed_holidays,
        )
    except LeaveDomainError as err:
        raise _translate_error(err) from err

    with transaction.atomic():
        req = LeaveRequest.objects.create(
            user_id=employee_user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            days_count=days_count,
            purpose=f"Offline sanction reference: {sanction_reference_number}",
            status=RequestStatus.APPROVED.value,  # Born closed/approved (BR-EL-029)
            department=department,
            is_offline_record=True,
        )

        OfflineLeaveRecord.objects.create(
            request=req,
            sanction_reference_number=sanction_reference_number,
            sanction_date=sanction_date,
            sanctioning_authority_name=sanctioning_authority_name,
            offline_reason=offline_reason,
            entered_by_user_id=principal.user_id,
        )

        # Debit balance immediately (BR-EL-029)
        LeaveLedgerEntry.objects.create(
            user_id=employee_user_id,
            category=category,
            delta_days=-days_count,
            transaction_type=LedgerTransactionType.DEBIT.value,
            reason=f"Offline sanctioned leave sync (Ref: {sanction_reference_number})",
            reference_id=str(req.id),
            created_by_user_id=principal.user_id,
        )

        # Audit trail (BR-EL-037)
        LeaveAuditEvent.objects.create(
            request=req,
            event=Event.OFFLINE_RECORD.value,
            from_state=RequestStatus.DRAFT.value,
            to_state=RequestStatus.APPROVED.value,
            actor_user_id=principal.user_id,
            actor_role="Leave Administrator",
            remarks=f"Offline sanctioned leave recorded (Authority: {sanctioning_authority_name})",
        )

        return req
