"""HR-EIS Query Scoping layer (BR-HR-002, BR-HR-003, BR-HR-030)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

from modules.hreis.models import (
    AppraisalSubmission,
    CpdaRequest,
    EmployeeServiceRecord,
    HrAuditLog,
    HrNotification,
    LeaveRequest,
    LtcRequest,
)

if TYPE_CHECKING:
    from fusion_auth.principal import Principal


def service_records_for(principal: Principal) -> QuerySet[EmployeeServiceRecord]:
    """HR Admin sees all; employee sees own service record only (BR-HR-003)."""
    if principal.has_permission("hr_eis.service_record.view_all"):
        return EmployeeServiceRecord.objects.all().order_by("user_id")
    return EmployeeServiceRecord.objects.filter(user_id=principal.user_id)


def leaves_for(principal: Principal) -> QuerySet[LeaveRequest]:
    """Employee sees own; Approvers see assigned requests or own requests."""
    is_approver = principal.has_permission("hr_eis.leave.review")
    if is_approver:
        # Match current authority role or applicant is self
        roles = [r.lower() for r in principal.roles]
        return LeaveRequest.objects.filter(
            Q(user_id=principal.user_id) | Q(current_authority_role__in=roles)
        ).distinct()
    return LeaveRequest.objects.filter(user_id=principal.user_id)


def appraisals_for(principal: Principal) -> QuerySet[AppraisalSubmission]:
    """Employee sees own; Reviewers/Director see assigned/submitted appraisals."""
    can_review = principal.has_permission("hr_eis.appraisal.review") or principal.has_permission(
        "hr_eis.appraisal.finalize"
    )
    is_admin = principal.has_permission("hr_eis.appraisal.assign_reviewer")

    if is_admin:
        return AppraisalSubmission.objects.all()

    if can_review:
        return AppraisalSubmission.objects.filter(
            Q(user_id=principal.user_id)
            | Q(status__in=["submitted", "under_review", "finalized"])
        ).distinct()

    return AppraisalSubmission.objects.filter(user_id=principal.user_id)


def ltc_requests_for(principal: Principal) -> QuerySet[LtcRequest]:
    """Scoping for LTC claims: applicant, HR admin (verify), approver, accountant."""
    is_admin = principal.has_permission("hr_eis.ltc.verify")
    is_approver = principal.has_permission("hr_eis.ltc.approve")
    is_accountant = principal.has_permission("hr_eis.ltc.settle")

    if is_admin or is_accountant:
        return LtcRequest.objects.all()

    if is_approver:
        roles = [r.lower() for r in principal.roles]
        return LtcRequest.objects.filter(
            Q(user_id=principal.user_id) | Q(current_authority_role__in=roles)
        ).distinct()

    return LtcRequest.objects.filter(user_id=principal.user_id)


def cpda_requests_for(principal: Principal) -> QuerySet[CpdaRequest]:
    """Scoping for CPDA claims: applicant, HR admin, approver, accountant."""
    is_admin = principal.has_permission("hr_eis.cpda.verify")
    is_approver = principal.has_permission("hr_eis.cpda.approve")
    is_accountant = principal.has_permission("hr_eis.cpda.settle")

    if is_admin or is_accountant:
        return CpdaRequest.objects.all()

    if is_approver:
        roles = [r.lower() for r in principal.roles]
        return CpdaRequest.objects.filter(
            Q(user_id=principal.user_id) | Q(current_authority_role__in=roles)
        ).distinct()

    return CpdaRequest.objects.filter(user_id=principal.user_id)


def audit_logs_for(principal: Principal) -> QuerySet[HrAuditLog]:
    """Audit logs are accessible ONLY to authorized HR Administrators (BR-HR-026)."""
    if principal.has_permission("hr_eis.audit.view"):
        return HrAuditLog.objects.all().order_by("-timestamp")
    return HrAuditLog.objects.none()


def notifications_for(principal: Principal) -> QuerySet[HrNotification]:
    """Users only see notifications addressed to them."""
    return HrNotification.objects.filter(user_id=principal.user_id).order_by("-created_at")
