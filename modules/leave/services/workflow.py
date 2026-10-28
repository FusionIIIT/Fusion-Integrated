from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationAudit,
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadRecommendation,
)
from modules.leave.services.ledger import debit_balance, refund_balance, ensure_balance


def _audit(app: LeaveApplication, actor_id: int, action: str, from_status: str, to_status: str, remarks: str = "") -> None:
    LeaveApplicationAudit.objects.create(
        application=app,
        actor_id=actor_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )


@transaction.atomic
def submit_application(app: LeaveApplication, actor_id: int) -> LeaveApplication:
    """
    Submits a leave application, triggers full validation, enforces balance checks,
    and routes through the substitute or Unit Head workflow.
    """
    if actor_id != app.user_id:
        raise ValidationError({"user_id": _("Only the applicant may submit their application.")})

    # Validate model and business rules
    app.full_clean()

    # Pre-submission balance availability check
    balance = ensure_balance(app.user_id, app.start_date.year, app.category)
    if Decimal(str(balance.available_balance)) < app.calculated_days:
        raise ValidationError({
            "balance": _(f"Insufficient {app.category} balance. Available: {balance.available_balance}, Required: {app.calculated_days}")
        })

    # Self-approval governance check (except Director under BR-EL-020)
    if app.unit_head_id and app.unit_head_id == app.user_id:
        raise ValidationError({"unit_head_id": _("Applicant cannot be their own Unit Head.")})
    if app.sanctioning_authority_id and app.sanctioning_authority_id == app.user_id:
        raise ValidationError({"sanctioning_authority_id": _("Applicant cannot sanction their own leave.")})

    old_status = app.status

    if app.substitute_id:
        app.status = LeaveStatus.SUBSTITUTE_PENDING
        app.substitute_status = SubstituteStatus.PENDING
    else:
        app.status = LeaveStatus.UNIT_HEAD_PENDING

    app.save()
    _audit(app, actor_id, "SUBMIT", old_status, app.status, "Application submitted.")
    return app


@transaction.atomic
def respond_substitute(app: LeaveApplication, actor_id: int, accept: bool, remarks: str = "") -> LeaveApplication:
    """
    BR-EL-015: Substitute consent gate.
    """
    if actor_id != app.substitute_id:
        raise ValidationError({"substitute_id": _("Only the nominated substitute can respond.")})
    if app.status != LeaveStatus.SUBSTITUTE_PENDING:
        raise ValidationError({"status": _("This application is not awaiting substitute consent.")})

    old_status = app.status
    if accept:
        app.substitute_status = SubstituteStatus.ACCEPTED
        app.status = LeaveStatus.UNIT_HEAD_PENDING
        action = "SUBSTITUTE_ACCEPT"
    else:
        app.substitute_status = SubstituteStatus.DECLINED
        action = "SUBSTITUTE_DECLINE"

    app.substitute_remarks = remarks
    app.save()
    _audit(app, actor_id, action, old_status, app.status, remarks)
    return app


@transaction.atomic
def unit_head_review(app: LeaveApplication, actor_id: int, approve_or_recommend: bool, remarks: str = "") -> LeaveApplication:
    """
    BR-EL-016 & BR-EL-017:
    - For CL and RH: Unit Head has final sanction authority.
    - For SCL, EL, COL, VL: Unit Head recommends or does not recommend; forwards to Sanctioning Authority.
    """
    if app.unit_head_id and actor_id != app.unit_head_id:
        raise ValidationError({"unit_head_id": _("Only the designated Unit Head can review this request.")})
    if actor_id == app.user_id:
        raise ValidationError({"unit_head_id": _("Unit Head cannot review their own leave request.")})
    if app.status != LeaveStatus.UNIT_HEAD_PENDING:
        raise ValidationError({"status": _("This application is not pending Unit Head review.")})

    old_status = app.status

    if app.category in (LeaveCategory.CL, LeaveCategory.RH):
        # Final decision by Unit Head
        if approve_or_recommend:
            app.status = LeaveStatus.APPROVED
            app.decided_at = timezone.now()
            debit_balance(app.user_id, app.start_date.year, app.category, app.calculated_days)
            action = "UNIT_HEAD_SANCTION_APPROVE"
        else:
            app.status = LeaveStatus.REJECTED
            app.decided_at = timezone.now()
            action = "UNIT_HEAD_SANCTION_REJECT"
    else:
        # Recommending step for higher-sanction categories
        app.unit_head_recommendation = (
            UnitHeadRecommendation.RECOMMENDED if approve_or_recommend else UnitHeadRecommendation.NOT_RECOMMENDED
        )
        app.status = LeaveStatus.SANCTIONING_PENDING
        action = "UNIT_HEAD_RECOMMEND" if approve_or_recommend else "UNIT_HEAD_NOT_RECOMMEND"

    app.unit_head_remarks = remarks
    app.save()
    _audit(app, actor_id, action, old_status, app.status, remarks)
    return app


@transaction.atomic
def sanction_decision(app: LeaveApplication, actor_id: int, approve: bool, remarks: str = "") -> LeaveApplication:
    """
    BR-EL-018: Final Sanctioning decision for higher-sanction leaves (EL, SCL, COL, VL).
    """
    if app.sanctioning_authority_id and actor_id != app.sanctioning_authority_id:
        raise ValidationError({"sanctioning_authority_id": _("Only the designated Sanctioning Authority may decide.")})
    if actor_id == app.user_id:
        raise ValidationError({"sanctioning_authority_id": _("Sanctioning Authority cannot self-sanction.")})
    if app.status != LeaveStatus.SANCTIONING_PENDING:
        raise ValidationError({"status": _("This application is not pending higher sanctioning decision.")})

    old_status = app.status
    if approve:
        app.status = LeaveStatus.APPROVED
        app.decided_at = timezone.now()
        debit_balance(app.user_id, app.start_date.year, app.category, app.calculated_days)
        action = "SANCTION_APPROVE"
    else:
        app.status = LeaveStatus.REJECTED
        app.decided_at = timezone.now()
        action = "SANCTION_REJECT"

    app.sanctioner_remarks = remarks
    app.save()
    _audit(app, actor_id, action, old_status, app.status, remarks)
    return app


@transaction.atomic
def withdraw_application(app: LeaveApplication, actor_id: int) -> LeaveApplication:
    """
    BR-EL-022: Immediate withdrawal of pending request prior to final approval.
    """
    if actor_id != app.user_id:
        raise ValidationError({"user_id": _("Only the applicant may withdraw their pending application.")})

    pending_statuses = [
        LeaveStatus.SUBMITTED,
        LeaveStatus.SUBSTITUTE_PENDING,
        LeaveStatus.UNIT_HEAD_PENDING,
        LeaveStatus.SANCTIONING_PENDING,
    ]
    if app.status not in pending_statuses:
        raise ValidationError({"status": _("Only pending applications can be withdrawn.")})

    old_status = app.status
    app.status = LeaveStatus.WITHDRAWN
    app.save()
    _audit(app, actor_id, "WITHDRAW", old_status, app.status, "Withdrawn by applicant.")
    return app


@transaction.atomic
def cancel_approved_leave(app: LeaveApplication, actor_id: int, reason: str) -> LeaveApplication:
    """
    BR-EL-023: Cancellation of approved leave before start. Restores leave balance.
    """
    if actor_id != app.user_id:
        raise ValidationError({"user_id": _("Only the applicant may request cancellation of their approved leave.")})
    if app.status != LeaveStatus.APPROVED:
        raise ValidationError({"status": _("Only approved leaves can be cancelled.")})

    if not reason or not reason.strip():
        raise ValidationError({"reason": _("Cancellation reason is required.")})

    today = timezone.now().date()
    if app.start_date <= today:
        raise ValidationError({"start_date": _("Cannot cancel leave that has already commenced; use resumption instead.")})

    old_status = app.status
    app.status = LeaveStatus.CANCELLED
    app.cancelled_at = timezone.now()
    app.cancellation_reason = reason

    # Restore debited balance
    refund_balance(app.user_id, app.start_date.year, app.category, app.calculated_days)

    app.save()
    _audit(app, actor_id, "CANCEL", old_status, app.status, reason)
    return app


@transaction.atomic
def submit_resumption(app: LeaveApplication, actor_id: int, actual_date: date, remarks: str = "") -> LeaveApplication:
    """
    BR-EL-027, BR-EL-028: Resumption submission and balance adjustment.
    """
    if actor_id != app.user_id:
        raise ValidationError({"user_id": _("Only the applicant may submit their joining report.")})
    if app.status != LeaveStatus.APPROVED:
        raise ValidationError({"status": _("Only approved leaves can have resumption submitted.")})
    if not actual_date:
        raise ValidationError({
            "actual_resumption_date": _("Actual resumption date is required.")
        })
    if actual_date < app.start_date:
        raise ValidationError({
            "actual_resumption_date": _("Actual resumption date cannot be earlier than leave start date.")
        })

    old_status = app.status
    app.actual_resumption_date = actual_date
    app.status = LeaveStatus.RESUMED

    # Calculate difference between scheduled end date and actual resumption
    # If resuming before end date, refund unavailed days
    if actual_date <= app.end_date:
        diff_days = (app.end_date - actual_date).days
        if diff_days > 0:
            refund_balance(app.user_id, app.start_date.year, app.category, Decimal(str(diff_days)))

    app.save()
    _audit(app, actor_id, "RESUME", old_status, app.status, f"Resumed on {actual_date}. {remarks}")
    return app
