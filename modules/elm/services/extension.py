"""Ongoing leave extension services (CW-EL-03 / EL-UC-009 / BR-EL-025)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.elm.domain.constants import (
    ApplicationStatus,
    ExtensionStatus,
    LeaveCategory,
    SubstituteStatus,
    TaskType,
)
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.state_machine import (
    transition_extension_final,
    transition_extension_unit_head,
)
from modules.elm.domain.validation import (
    validate_balance_sufficient,
    validate_substitute_eligibility,
)
from modules.elm.models import (
    LeaveAuditLog,
    LeaveExtension,
    WorkflowTask,
)
from modules.elm.selectors.balances import get_balances_for_user
from modules.elm.selectors.calendars import get_closed_holidays_set
from modules.elm.selectors.leaves import (
    get_application_by_id,
    get_substitute_active_leaves,
)
from modules.elm.services.balances import debit_leave_balance


@transaction.atomic
def request_extension(
    application_id: int,
    applicant_user_id: int,
    extended_end_date: date,
    reason: str,
    *,
    requires_substitute: bool = False,
    substitute_user_id: int | None = None,
    today: date | None = None,
) -> LeaveExtension:
    """Request extension for ongoing EL, COL, or VL (EL-UC-009, BR-EL-025)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.user_id != applicant_user_id:
        raise BadRequestError("Only the applicant can request an extension of their leave.")

    # BR-EL-025: Extension available only for ongoing EL, COL, or VL
    if app.category not in (
        LeaveCategory.EL.value,
        LeaveCategory.COL.value,
        LeaveCategory.VL.value,
    ):
        raise BadRequestError(
            f"Extensions are only permitted for EL, COL, and VL. Not permitted for {app.category}."
        )
    # Must be approved and ongoing (started, or before/at end date)
    if app.status != ApplicationStatus.APPROVED.value:
        raise ConflictError(f"Cannot extend leave in state '{app.status}'. Must be APPROVED.")

    if extended_end_date <= app.end_date:
        raise BadRequestError(
            f"Extended end date ({extended_end_date}) must be after current end date "
            f"({app.end_date})."
        )

    # Extension start date is the day after current end date
    ext_start = app.end_date + timezone.timedelta(days=1)
    year = ext_start.year
    closed_holidays = get_closed_holidays_set(year)

    incremental_days = calculate_chargeable_days(
        app.category,
        ext_start,
        extended_end_date,
        closed_holidays=closed_holidays,
    )

    # Validate balance for incremental days
    balances = get_balances_for_user(applicant_user_id, year)
    avail_balance = balances.get(app.category, Decimal("0.00"))
    try:
        validate_balance_sufficient(avail_balance, incremental_days, app.category)
    except ValueError as e:
        raise BadRequestError(str(e)) from e

    # Validate substitute if nominated
    if requires_substitute and substitute_user_id:
        user_map = directory.get_users([substitute_user_id])
        sub_dto = user_map.get(substitute_user_id)
        sub_kind = sub_dto.kind if sub_dto else None
        sub_leaves = get_substitute_active_leaves(substitute_user_id)
        try:
            validate_substitute_eligibility(
                applicant_user_id,
                substitute_user_id,
                sub_kind,
                sub_leaves,
                ext_start,
                extended_end_date,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e

    initial_status = (
        ExtensionStatus.AWAITING_SUBSTITUTE
        if requires_substitute and substitute_user_id
        else ExtensionStatus.AWAITING_UNIT_HEAD
    )

    ext = LeaveExtension.objects.create(
        leave_application=app,
        applicant_user_id=applicant_user_id,
        extended_start_date=ext_start,
        extended_end_date=extended_end_date,
        incremental_days=incremental_days,
        reason=reason,
        requires_substitute=requires_substitute and bool(substitute_user_id),
        substitute_user_id=substitute_user_id if requires_substitute else None,
        substitute_status=(
            SubstituteStatus.PENDING.value
            if requires_substitute and substitute_user_id
            else SubstituteStatus.NONE.value
        ),
        status=initial_status.value,
    )

    # Assign task
    if initial_status == ExtensionStatus.AWAITING_SUBSTITUTE and substitute_user_id:
        WorkflowTask.objects.create(
            extension=ext,
            task_type=TaskType.EXTENSION_SUBSTITUTE.value,
            assigned_to_user_id=substitute_user_id,
            status="pending",
        )
    elif initial_status == ExtensionStatus.AWAITING_UNIT_HEAD and app.unit_head_user_id:
        WorkflowTask.objects.create(
            extension=ext,
            task_type=TaskType.EXTENSION_UNIT_HEAD.value,
            assigned_to_user_id=app.unit_head_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=applicant_user_id,
        action="request_extension",
        from_state=app.status,
        to_state=initial_status.value,
        remarks=f"Requested extension of {incremental_days} days until {extended_end_date}",
        payload={"extension_id": ext.id, "incremental_days": str(incremental_days)},
    )

    return ext


@transaction.atomic
def review_extension_unit_head(
    extension_id: int,
    reviewer_user_id: int,
    outcome: str,
    remarks: str = "",
) -> LeaveExtension:
    """Review ongoing leave extension at Unit Head."""
    ext = LeaveExtension.objects.select_related("leave_application").filter(id=extension_id).first()
    if not ext:
        raise NotFoundError(f"Extension #{extension_id} not found.")

    current_status = ExtensionStatus(ext.status)
    app = ext.leave_application
    if app.unit_head_user_id and app.unit_head_user_id != reviewer_user_id:
        raise PermissionDeniedError("Only the assigned Unit Head may review this extension.")
    requires_estt = bool(app.establishment_user_id)

    try:
        new_status = transition_extension_unit_head(
            current_status, outcome, requires_establishment=requires_estt
        )
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = ext.status
    ext.status = new_status.value
    ext.unit_head_recommendation = outcome
    ext.unit_head_action_at = timezone.now()
    ext.unit_head_remarks = remarks
    ext.save()

    WorkflowTask.objects.filter(
        extension=ext,
        task_type=TaskType.EXTENSION_UNIT_HEAD.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    if new_status == ExtensionStatus.AWAITING_ESTABLISHMENT and app.establishment_user_id:
        WorkflowTask.objects.create(
            extension=ext,
            task_type=TaskType.EXTENSION_ESTABLISHMENT.value,
            assigned_to_user_id=app.establishment_user_id,
            status="pending",
        )
    elif (
        new_status == ExtensionStatus.AWAITING_FINAL_DECISION
        and app.sanctioning_authority_user_id
    ):
        WorkflowTask.objects.create(
            extension=ext,
            task_type=TaskType.EXTENSION_FINAL.value,
            assigned_to_user_id=app.sanctioning_authority_user_id,
            status="pending",
        )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=reviewer_user_id,
        action="extension_unit_head_review",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or outcome,
        payload={"extension_id": ext.id, "outcome": outcome},
    )

    return ext


@transaction.atomic
def review_extension_final(
    extension_id: int,
    sanctioner_user_id: int,
    decision: str,
    remarks: str = "",
) -> LeaveExtension:
    """Final decision on extension by Sanctioning Authority."""
    ext = LeaveExtension.objects.select_related("leave_application").filter(id=extension_id).first()
    if not ext:
        raise NotFoundError(f"Extension #{extension_id} not found.")

    app = ext.leave_application
    if (
        app.sanctioning_authority_user_id
        and app.sanctioning_authority_user_id != sanctioner_user_id
    ):
        raise PermissionDeniedError(
            "Only the assigned Sanctioning Authority may review this extension."
        )

    current_status = ExtensionStatus(ext.status)
    try:
        new_status = transition_extension_final(current_status, decision)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = ext.status
    ext.status = new_status.value
    ext.decision_by_user_id = sanctioner_user_id
    ext.decision_at = timezone.now()
    ext.decision_remarks = remarks
    ext.save()

    app = ext.leave_application

    # BR-EL-025 / AFR-EL-020.6: If approved, post ONLY incremental additional leave period
    # and update base leave end date. If rejected, original ongoing leave preserved unchanged.
    if new_status == ExtensionStatus.APPROVED:
        debit_leave_balance(
            user_id=ext.applicant_user_id,
            year=ext.extended_start_date.year,
            category=app.category,
            amount=ext.incremental_days,
            reference_id=f"ext-{ext.id}",
            remarks=f"Extension #{ext.id} of leave #{app.id}",
            performed_by_user_id=sanctioner_user_id,
        )
        # Update base leave end date and chargeable days
        app.end_date = ext.extended_end_date
        app.chargeable_days += ext.incremental_days
        app.save(update_fields=["end_date", "chargeable_days", "updated_at"])

    WorkflowTask.objects.filter(
        extension=ext,
        task_type=TaskType.EXTENSION_FINAL.value,
        status="pending",
    ).update(status="completed", completed_at=timezone.now())

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=sanctioner_user_id,
        action="extension_final_decision",
        from_state=from_state,
        to_state=new_status.value,
        remarks=remarks or decision,
        payload={"extension_id": ext.id, "decision": decision},
    )

    return ext
