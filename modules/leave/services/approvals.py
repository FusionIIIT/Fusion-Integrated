"""Approval and review workflows (EL-UC-003..005, EL-UC-008, EL-UC-011, BR-EL-016..020)."""
from __future__ import annotations

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.hierarchy import is_unit_head_final
from modules.leave.domain.state_machine import validate_transition
from modules.leave.models import (
    LeaveActionHistory,
    LeaveApplication,
    LeaveBalance,
    LeaveLedgerEntry,
)
from modules.leave.selectors.applications import get_application_by_id
from modules.leave.selectors.balances import get_or_create_balance
from modules.leave.services.notifications import enqueue as enqueue_notification


@transaction.atomic
def review_by_unit_head(
    *,
    reviewer_user_id: int,
    application_id: int,
    recommended: bool,
    remarks: str = "",
) -> LeaveApplication:
    """Unit Head review action (EL-UC-003, BR-EL-016, BR-EL-017)."""
    app = get_application_by_id(application_id, for_update=True)
    if app.status not in {"under_review", "extension_requested", "cancel_requested"}:
        raise ConflictError(f"Application is in status {app.status!r}, not under review.", code="not_under_review")

    if app.status == "cancel_requested" and is_unit_head_final(app.category):
        return process_cancellation_decision(
            reviewer_user_id=reviewer_user_id, application_id=application_id,
            decision="approved" if recommended else "rejected", remarks=remarks,
        )

    app.unit_head_user_id = reviewer_user_id
    app.unit_head_recommended = recommended
    app.unit_head_remarks = remarks
    app.unit_head_reviewed_at = timezone.now()

    if is_unit_head_final(app.category):
        if recommended:
            _approve_and_deduct(app, sanctioned_by_user_id=reviewer_user_id, remarks=remarks)
        else:
            app.status = "rejected"
            app.save(update_fields=["status", "unit_head_user_id", "unit_head_recommended", "unit_head_remarks", "unit_head_reviewed_at", "updated_at"])
            LeaveActionHistory.objects.create(
                application=app, actor_user_id=reviewer_user_id, actor_role="unit_head",
                action="rejected", remarks=remarks,
            )
            enqueue_notification(
                recipient_user_id=app.user_id, topic="application.decision",
                dedupe_key=f"leave:{app.pk}:decision:unit-rejected",
                subject="Leave request rejected", body=f"Leave request #{app.pk} was rejected by the Unit Head.",
            )
    else:
        app.save(update_fields=["unit_head_user_id", "unit_head_recommended", "unit_head_remarks", "unit_head_reviewed_at", "updated_at"])
        action_name = "recommended" if recommended else "not_recommended"
        LeaveActionHistory.objects.create(
            application=app, actor_user_id=reviewer_user_id, actor_role="unit_head",
            action=action_name, remarks=remarks,
        )
        enqueue_notification(
            recipient_user_id=app.establishment_user_id or app.sanctioning_authority_user_id,
            topic="application.assigned", dedupe_key=f"leave:{app.pk}:higher-assigned",
            subject="Leave request requires higher review",
            body=f"Leave request #{app.pk} is ready for the next configured review step.",
        )

    return app


@transaction.atomic
def sanction_application(
    *, sanctioner_user_id: int, application_id: int, decision: str,
    remarks: str = "", role_name: str = "sanctioning_authority",
) -> LeaveApplication:
    """Final sanctioning decision for higher-sanction categories."""
    app = get_application_by_id(application_id, for_update=True)
    if app.status not in {"under_review", "extension_requested"}:
        raise ConflictError(f"Application is in status {app.status!r}, not under review.", code="not_under_review")

    if decision == "approved":
        _approve_and_deduct(app, sanctioned_by_user_id=sanctioner_user_id, remarks=remarks, role_name=role_name)
    elif decision == "rejected":
        app.status = "rejected"
        app.sanctioning_authority_user_id = sanctioner_user_id
        app.sanctioning_remarks = remarks
        app.sanctioned_at = timezone.now()
        app.save(update_fields=["status", "sanctioning_authority_user_id", "sanctioning_remarks", "sanctioned_at", "updated_at"])
        LeaveActionHistory.objects.create(
            application=app, actor_user_id=sanctioner_user_id, actor_role=role_name,
            action="rejected", remarks=remarks,
        )
        enqueue_notification(
            recipient_user_id=app.user_id, topic="application.decision",
            dedupe_key=f"leave:{app.pk}:decision:rejected",
            subject="Leave request rejected", body=f"Leave request #{app.pk} was rejected by the sanctioning authority.",
        )
    else:
        raise BadRequestError("Decision must be 'approved' or 'rejected'.", code="invalid_decision")
    return app


def _approve_and_deduct(
    app: LeaveApplication, sanctioned_by_user_id: int, remarks: str = "",
    role_name: str = "authority",
) -> None:
    balance = get_or_create_balance(app.user_id, app.start_date.year)
    balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
    available = balance.get_category_balance(app.category)
    reserved = LeaveApplication.objects.filter(
        user_id=app.user_id, category=app.category, start_date__year=app.start_date.year,
        status__in=["substitute_pending", "under_review", "extension_requested"],
    ).exclude(pk=app.pk).aggregate(total=Sum("days_count"))["total"] or Decimal("0.0")
    if available - reserved < app.days_count:
        raise ConflictError(
            f"Cannot approve: applicant has insufficient unreserved {app.category} balance ({available - reserved} available).",
            code="insufficient_balance",
        )

    balance.deduct(app.category, app.days_count)
    balance.save()
    LeaveLedgerEntry.objects.create(
        balance=balance, user_id=app.user_id, category=app.category, entry_type="debit",
        change_amount=-app.days_count, balance_after=balance.get_category_balance(app.category),
        reference_id=app.pk, remarks=f"Leave approved for {app.start_date} to {app.end_date}",
    )
    app.status = "approved"
    app.sanctioning_authority_user_id = sanctioned_by_user_id
    app.sanctioning_remarks = remarks
    app.sanctioned_at = timezone.now()
    app.save(update_fields=["status", "sanctioning_authority_user_id", "sanctioning_remarks", "sanctioned_at", "updated_at"])
    LeaveActionHistory.objects.create(
        application=app, actor_user_id=sanctioned_by_user_id, actor_role=role_name,
        action="sanctioned", remarks=remarks,
    )
    enqueue_notification(
        recipient_user_id=app.user_id, topic="application.decision",
        dedupe_key=f"leave:{app.pk}:decision:approved",
        subject="Leave request approved", body=f"Leave request #{app.pk} was approved.",
    )


@transaction.atomic
def process_cancellation_decision(
    *, reviewer_user_id: int, application_id: int, decision: str, remarks: str = "",
) -> LeaveApplication:
    """Review cancellation request; rejection leaves the original approved leave intact."""
    app = get_application_by_id(application_id, for_update=True)
    if app.status != "cancel_requested":
        raise ConflictError("Application is not in cancellation requested status.", code="not_cancel_requested")
    # Resolve the original record before either branch; both outcomes notify its owner.
    original = app.parent_leave or app

    if decision == "approved":
        balance = get_or_create_balance(original.user_id, original.start_date.year)
        balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
        balance.credit(original.category, original.days_count)
        balance.save()
        LeaveLedgerEntry.objects.create(
            balance=balance, user_id=original.user_id, category=original.category,
            entry_type="reversal", change_amount=original.days_count,
            balance_after=balance.get_category_balance(original.category), reference_id=original.pk,
            remarks="Leave cancelled; balance restored",
        )
        original.status = "cancelled"
        original.cancelled_at = timezone.now()
        original.save(update_fields=["status", "cancelled_at", "updated_at"])
        app.status = "cancelled"
        app.cancelled_at = timezone.now()
        app.save(update_fields=["status", "cancelled_at", "updated_at"])
        LeaveActionHistory.objects.create(
            application=app, actor_user_id=reviewer_user_id, actor_role="authority",
            action="cancellation_approved", remarks=remarks,
        )
        enqueue_notification(
            recipient_user_id=original.user_id, topic="cancellation.decision",
            dedupe_key=f"leave:{app.pk}:cancellation:approved",
            subject="Leave cancellation approved", body=f"Cancellation request #{app.pk} was approved.",
        )
    elif decision == "rejected":
        app.status = "rejected"
        app.save(update_fields=["status", "updated_at"])
        LeaveActionHistory.objects.create(
            application=app, actor_user_id=reviewer_user_id, actor_role="authority",
            action="cancellation_rejected", remarks=remarks,
        )
        enqueue_notification(
            recipient_user_id=original.user_id, topic="cancellation.decision",
            dedupe_key=f"leave:{app.pk}:cancellation:rejected",
            subject="Leave cancellation rejected",
            body=f"Cancellation request #{app.pk} was rejected; the original leave remains approved.",
        )
    else:
        raise BadRequestError("Decision must be 'approved' or 'rejected'.", code="invalid_decision")
    return app


@transaction.atomic
def forward_to_sanctioning_authority(*, establishment_user_id: int, application_id: int, remarks: str = "") -> LeaveApplication:
    """Complete configured Establishment routing without making the final decision."""
    app = get_application_by_id(application_id, for_update=True)
    if app.establishment_user_id != establishment_user_id:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("This request is not assigned to your Establishment role.")
    if app.status not in {"under_review", "extension_requested", "cancel_requested"}:
        raise ConflictError("This request is not awaiting Establishment processing.", code="not_pending_establishment")
    if app.establishment_reviewed_at:
        raise ConflictError("Establishment has already forwarded this request.", code="already_forwarded")
    app.establishment_remarks = remarks
    app.establishment_reviewed_at = timezone.now()
    app.save(update_fields=["establishment_remarks", "establishment_reviewed_at", "updated_at"])
    LeaveActionHistory.objects.create(
        application=app, actor_user_id=establishment_user_id, actor_role="establishment",
        action="forwarded_to_authority", remarks=remarks,
    )
    enqueue_notification(
        recipient_user_id=app.sanctioning_authority_user_id,
        topic="application.forwarded", dedupe_key=f"leave:{app.pk}:forwarded",
        subject="Leave request ready for sanction", body=f"Leave request #{app.pk} is ready for your decision.",
    )
    return app
