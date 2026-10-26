"""Review and Decide Leave Request service (HR-UC-004 / ReviewDecideRequestControl / BW-HR-01 Terminal)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory_contracts
from modules.leave.domain import state_machine as sm
from modules.leave.domain.entities import ApprovalOutcome
from modules.leave.domain.rules import determine_next_authority
from modules.leave.models import ApprovalDecision, ApprovingAuthority, LeaveRequest
from modules.leave.services.balances import deduct_leave_balance


def decide_leave_request(
    request_id: int,
    authority_user_id: int,
    outcome: str,
    remarks: str = "",
    next_authority_id: int | None = None,
    is_admin_override: bool = False,
) -> ApprovalDecision:
    """Record a review decision for a routed leave request and trigger balance update on approval.

    Enforces:
    - BR-HR-002: Authority RBAC authorization
    - BR-HR-023: Permitted outcomes and workflow order preservation (Approved, Rejected, Forwarded)
    - BR-HR-010: Automated leave balance update upon approval
    - BW-HR-01 (Direct path), BW-HR-02 (Rejection), BW-HR-03 (Forwarding loop traversal)
    """
    with transaction.atomic():
        leave_request = (
            LeaveRequest.objects.select_for_update()
            .filter(id=request_id)
            .first()
        )
        if not leave_request:
            raise NotFoundError(f"Leave request #{request_id} not found.")

        # Invariant check: workflow order must be preserved (BR-HR-023)
        if leave_request.status != LeaveRequest.Status.PENDING_CURRENT_AUTHORITY:
            raise ConflictError(
                f"Cannot decide on leave request in status {leave_request.status!r}; "
                f"must be {LeaveRequest.Status.PENDING_CURRENT_AUTHORITY!r}."
            )

        # RBAC & Authority authorization check (BR-HR-002)
        if not is_admin_override:
            is_assigned = (
                leave_request.current_authority_id is None
                or leave_request.current_authority_id == authority_user_id
            )
            is_auth_role = ApprovingAuthority.objects.filter(
                user_id=authority_user_id,
                is_active=True,
            ).exists()
            if not is_assigned and not is_auth_role:
                raise PermissionDeniedError(
                    "You are not the designated approving authority for this request."
                )

        if outcome == ApprovalOutcome.FORWARDED.value:
            # Multi-tier routing escalation (BW-HR-03 / BR-HR-009)
            target_status = LeaveRequest.Status.PENDING_CURRENT_AUTHORITY
            sm.resolve(sm.PENDING_CURRENT_AUTHORITY, sm.PENDING_CURRENT_AUTHORITY, sm.AUTHORITY)

            # Resolve next authority
            next_auth_id = next_authority_id
            next_role_str = ""

            if next_auth_id is not None:
                next_auth = ApprovingAuthority.objects.filter(user_id=next_auth_id, is_active=True).first()
                if not next_auth:
                    raise BadRequestError(f"Specified next authority #{next_auth_id} is not an active authority.")
                next_role_str = next_auth.role
            else:
                # Automatic escalation
                users_info = directory_contracts.get_users([leave_request.user_id])
                category = users_info.get(leave_request.user_id, {}).get("kind", "staff")

                active_auths = ApprovingAuthority.objects.filter(is_active=True)
                auth_dir = {a.role: a.user_id for a in active_auths}
                resolved_id, resolved_role = determine_next_authority(
                    current_role=leave_request.current_authority_role,
                    employee_category=category,
                    authority_directory=auth_dir,
                )
                if not resolved_id:
                    raise ConflictError(
                        "No higher authority available in hierarchy to forward this request to."
                    )
                next_auth_id = resolved_id
                next_role_str = resolved_role.value if resolved_role else ""

            # Update request with forwarded destination
            leave_request.current_authority_id = next_auth_id
            leave_request.current_authority_role = next_role_str
            leave_request.forward_count += 1
            leave_request.save(update_fields=["current_authority_id", "current_authority_role", "forward_count", "updated_at"])

            decision = ApprovalDecision.objects.create(
                request=leave_request,
                authority_id=authority_user_id,
                next_authority_id=next_auth_id,
                outcome=outcome,
                remarks=remarks.strip(),
            )
            return decision

        target_status = (
            LeaveRequest.Status.APPROVED
            if outcome == ApprovalOutcome.APPROVED.value
            else LeaveRequest.Status.REJECTED
        )

        # State machine transition check
        sm.resolve(sm.PENDING_CURRENT_AUTHORITY, target_status, sm.AUTHORITY)

        # Update leave request status
        leave_request.status = target_status
        leave_request.save(update_fields=["status", "updated_at"])

        # Create decision record
        decision = ApprovalDecision.objects.create(
            request=leave_request,
            authority_id=authority_user_id,
            outcome=outcome,
            remarks=remarks.strip(),
        )

        # Automated leave balance deduction on approval (BR-HR-010)
        if target_status == LeaveRequest.Status.APPROVED:
            deduct_leave_balance(
                user_id=leave_request.user_id,
                leave_type=leave_request.leave_type,
                days=leave_request.duration_days,
                year=leave_request.start_date.year,
            )

    return decision
