"""Leave Management events."""
from core.events.outbox import emit
from .models import LeaveRequest, SubstituteRequest, OfflineLeaveEntry


PRODUCES = (
    "leave.leave_request.created",
    "leave.leave_request.submitted",
    "leave.substitute_request.created",
    "leave.substitute_request.accepted",
    "leave.substitute_request.declined",
    "leave.leave_request.unit_head_reviewed",
    "leave.leave_request.establishment_reviewed",
    "leave.leave_request.final_sanctioned",
    "leave.leave_request.modified",
    "leave.leave_request.withdrawn",
    "leave.leave_request.cancelled",
    "leave.leave_request.extended",
    "leave.leave_request.resumed",
    "leave.offline_leave.recorded",
    "leave.year_end.processed",
)


def register() -> None:
    """Register event handlers."""
    # No handlers for now - other modules may subscribe to leave events
    pass


def emit_leave_request_created(leave_request: LeaveRequest, principal) -> None:
    emit(
        "leave.leave_request.created",
        {
            "leave_request_id": leave_request.id,
            "user_id": leave_request.user_id,
            "category": leave_request.category,
            "start_date": leave_request.start_date.isoformat(),
            "end_date": leave_request.end_date.isoformat(),
            "total_days": str(leave_request.total_days),
        },
        dedupe_key=f"leave_request.created:{leave_request.id}",
    )


def emit_leave_request_submitted(leave_request: LeaveRequest, principal) -> None:
    emit(
        "leave.leave_request.submitted",
        {
            "leave_request_id": leave_request.id,
            "user_id": leave_request.user_id,
            "category": leave_request.category,
            "status": leave_request.status,
        },
        dedupe_key=f"leave_request.submitted:{leave_request.id}",
    )


def emit_substitute_created(leave_request: LeaveRequest, substitute_request: SubstituteRequest, principal) -> None:
    emit(
        "leave.substitute_request.created",
        {
            "substitute_request_id": substitute_request.id,
            "leave_request_id": leave_request.id,
            "substitute_id": substitute_request.substitute_id,
            "nominated_by": substitute_request.nominated_by,
        },
        dedupe_key=f"substitute.created:{substitute_request.id}",
    )


def emit_substitute_accepted(leave_request: LeaveRequest, principal) -> None:
    emit(
        "leave.substitute_request.accepted",
        {
            "leave_request_id": leave_request.id,
            "substitute_id": leave_request.substitute_id,
            "accepted_by": principal.user_id,
        },
        dedupe_key=f"substitute.accepted:{leave_request.id}",
    )


def emit_substitute_declined(leave_request: LeaveRequest, principal, reason: str) -> None:
    emit(
        "leave.substitute_request.declined",
        {
            "leave_request_id": leave_request.id,
            "substitute_id": leave_request.substitute_id,
            "declined_by": principal.user_id,
            "reason": reason,
        },
        dedupe_key=f"substitute.declined:{leave_request.id}",
    )


def emit_unit_head_reviewed(leave_request: LeaveRequest, recommend: bool, principal) -> None:
    emit(
        "leave.leave_request.unit_head_reviewed",
        {
            "leave_request_id": leave_request.id,
            "recommend": recommend,
            "unit_head_id": principal.user_id,
            "new_status": leave_request.status,
        },
        dedupe_key=f"unit_head.reviewed:{leave_request.id}:{leave_request.status}",
    )


def emit_establishment_reviewed(leave_request: LeaveRequest, action: str, principal) -> None:
    emit(
        "leave.leave_request.establishment_reviewed",
        {
            "leave_request_id": leave_request.id,
            "action": action,
            "establishment_id": principal.user_id,
            "new_status": leave_request.status,
        },
        dedupe_key=f"establishment.reviewed:{leave_request.id}:{leave_request.status}",
    )


def emit_final_sanction(leave_request: LeaveRequest, approve: bool, principal) -> None:
    emit(
        "leave.leave_request.final_sanctioned",
        {
            "leave_request_id": leave_request.id,
            "approve": approve,
            "final_authority_id": principal.user_id,
            "new_status": leave_request.status,
        },
        dedupe_key=f"final_sanction:{leave_request.id}:{leave_request.status}",
    )


def emit_offline_leave_recorded(offline_entry: OfflineLeaveEntry, principal) -> None:
    emit(
        "leave.offline_leave.recorded",
        {
            "offline_entry_id": offline_entry.id,
            "user_id": offline_entry.user_id,
            "category": offline_entry.category,
            "total_days": str(offline_entry.total_days),
        },
        dedupe_key=f"offline_leave.recorded:{offline_entry.id}",
    )


def emit_year_end_processed(year: int, processed: int, errors: list) -> None:
    emit(
        "leave.year_end.processed",
        {
            "year": year,
            "processed_users": processed,
            "error_count": len(errors),
        },
        dedupe_key=f"year_end:{year}",
    )