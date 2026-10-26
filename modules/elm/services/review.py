"""Review and sanction workflow services (EL-UC-003, EL-UC-004, EL-UC-005).

Enforces BR-EL-016 through BR-EL-020 and BR-EL-036.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import LeaveCategory
from modules.elm.domain.state_machine import validate_unit_head_decision
from modules.elm.models import LeaveApplication, LeaveBalance
from modules.elm.services.audit import record_audit


def review_unit_head(
    actor,
    application_id: int,
    outcome: str,  # "RECOMMENDED", "NOT_RECOMMENDED", "APPROVE", "REJECT"
    remarks: str = "",
    has_establishment_step: bool = False,
) -> LeaveApplication:
    """Unit Head review (EL-UC-003).

    - CL/RH: Unit Head makes final approve/reject decision (BR-EL-016).
    - SCL/EL/COL/VL: Unit Head records recommendation and forwards (BR-EL-017).
    """
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().select_related("leave_type").get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id == user_id:
            raise PermissionDeniedError("Unit Head cannot review their own application.", code="self_review")

        if app.status != "AWAITING_UNIT_HEAD":
            raise ConflictError(
                f"Application #{application_id} is in status '{app.status}', not awaiting Unit Head review.",
                code="invalid_state",
            )

        from_status = app.status
        next_status = validate_unit_head_decision(
            category=app.leave_type.code,
            outcome=outcome,
            has_establishment_step=has_establishment_step,
        )

        app.unit_head_id = user_id
        app.unit_head_remarks = remarks
        app.unit_head_decided_at = timezone.now()
        app.unit_head_recommendation = outcome.upper()
        app.status = next_status.value

        # For CL/RH final approval, deduct balance now (BR-EL-016)
        if app.leave_type.code in (LeaveCategory.CL.value, LeaveCategory.RH.value):
            if next_status.value == "APPROVED":
                balance = LeaveBalance.objects.select_for_update().get(
                    employee_id=app.employee_id,
                    leave_type=app.leave_type,
                    year=app.start_date.year,
                )
                balance.used += app.days
                balance.save(update_fields=["used", "updated_at"])
                app.decided_at = timezone.now()
            elif next_status.value == "REJECTED":
                app.decided_at = timezone.now()

        app.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action=f"UNIT_HEAD_{outcome.upper()}",
            from_status=from_status,
            to_status=app.status,
            remarks=remarks,
        )

    return app


def route_establishment(
    actor,
    application_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Establishment verification and routing (EL-UC-004, BR-EL-019)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.status != "AWAITING_ESTABLISHMENT":
            raise ConflictError("Application is not awaiting establishment routing.", code="invalid_state")

        from_status = app.status
        app.establishment_id = user_id
        app.establishment_remarks = remarks
        app.establishment_routed_at = timezone.now()
        app.status = "AWAITING_SANCTION"
        app.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action="ESTABLISHMENT_ROUTE",
            from_status=from_status,
            to_status=app.status,
            remarks=remarks,
        )

    return app


def decide_sanction(
    actor,
    application_id: int,
    approve: bool,
    sanctioning_role: str = "Dean",
    remarks: str = "",
) -> LeaveApplication:
    """Final sanction decision by competent authority (EL-UC-005, BR-EL-018)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().select_related("leave_type").get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id == user_id:
            raise PermissionDeniedError("Cannot sanction own application.", code="self_sanction")

        if app.status != "AWAITING_SANCTION":
            raise ConflictError("Application is not awaiting sanction decision.", code="invalid_state")

        from_status = app.status

        if approve:
            # Deduct balance on approval
            balance = LeaveBalance.objects.select_for_update().get(
                employee_id=app.employee_id,
                leave_type=app.leave_type,
                year=app.start_date.year,
            )
            balance.used += app.days
            balance.save(update_fields=["used", "updated_at"])
            app.status = "APPROVED"
            action_name = "SANCTION_APPROVE"
        else:
            app.status = "REJECTED"
            action_name = "SANCTION_REJECT"

        app.sanctioning_authority_id = user_id
        app.sanctioning_authority_role = sanctioning_role
        app.remarks = remarks
        app.decided_at = timezone.now()
        app.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action=action_name,
            from_status=from_status,
            to_status=app.status,
            remarks=remarks,
        )

    return app


def self_sanction_director(
    actor,
    application_id: int,
    approve: bool,
    remarks: str = "",
) -> LeaveApplication:
    """Director self-sanction path (BR-EL-020)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().select_related("leave_type").get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id != user_id:
            raise PermissionDeniedError("Only the Director applicant can execute self-sanction.", code="not_director")

        if app.status != "AWAITING_DIRECTOR_SELF_SANCTION":
            raise ConflictError("Application is not awaiting Director self-sanction.", code="invalid_state")

        from_status = app.status

        if approve:
            balance = LeaveBalance.objects.select_for_update().get(
                employee_id=app.employee_id,
                leave_type=app.leave_type,
                year=app.start_date.year,
            )
            balance.used += app.days
            balance.save(update_fields=["used", "updated_at"])
            app.status = "APPROVED"
            action_name = "DIRECTOR_SELF_APPROVE"
        else:
            app.status = "REJECTED"
            action_name = "DIRECTOR_SELF_REJECT"

        app.sanctioning_authority_id = user_id
        app.sanctioning_authority_role = "Director"
        app.remarks = remarks
        app.decided_at = timezone.now()
        app.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action=action_name,
            from_status=from_status,
            to_status=app.status,
            remarks=remarks,
        )

    return app
