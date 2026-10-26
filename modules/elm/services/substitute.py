"""Substitute response and replacement services (EL-UC-002, EL-UC-019).

Enforces BR-EL-014 and BR-EL-015.
"""
from __future__ import annotations

import datetime
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.eligibility import ExistingLeaveSpan, check_substitute_eligibility
from modules.elm.models import LeaveApplication
from modules.elm.selectors.applications import get_active_leaves_for_employee
from modules.elm.services.audit import record_audit


def respond_to_substitute(
    actor,
    application_id: int,
    accept: bool,
    declined_reason: str = "",
    is_director_applicant: bool = False,
) -> LeaveApplication:
    """Nominated substitute accepts or declines the responsibility assignment (EL-UC-002)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.substitute_id != user_id:
            raise PermissionDeniedError("Only the nominated substitute can respond to this request.", code="not_substitute")

        if app.status != "AWAITING_SUBSTITUTE" or app.substitute_status != "PENDING":
            raise ConflictError("Application is not awaiting substitute response.", code="invalid_state")

        from_status = app.status

        if accept:
            app.substitute_status = "ACCEPTED"
            app.substitute_responded_at = timezone.now()
            # Releases consent gate (BR-EL-015)
            if is_director_applicant:
                app.status = "AWAITING_DIRECTOR_SELF_SANCTION"
            else:
                app.status = "AWAITING_UNIT_HEAD"
            action_name = "SUBSTITUTE_ACCEPT"
        else:
            app.substitute_status = "DECLINED"
            app.substitute_declined_reason = declined_reason
            app.substitute_responded_at = timezone.now()
            # Consent gate stays closed; applicant action required (BR-EL-015)
            app.status = "APPLICANT_ACTION_REQUIRED"
            action_name = "SUBSTITUTE_DECLINE"

        app.save()
        record_audit(
            application=app,
            actor_id=user_id,
            action=action_name,
            from_status=from_status,
            to_status=app.status,
            remarks=declined_reason if not accept else "Accepted substitute responsibility.",
        )

    return app


def nominate_replacement_substitute(
    actor,
    application_id: int,
    new_substitute_id: int,
) -> LeaveApplication:
    """Applicant nominates another eligible substitute after previous decline (EL-UC-019)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id != user_id:
            raise PermissionDeniedError("Only the applicant can nominate a replacement substitute.", code="not_applicant")

        if app.status != "APPLICANT_ACTION_REQUIRED":
            raise ConflictError(
                f"Application is in '{app.status}', not 'APPLICANT_ACTION_REQUIRED'.",
                code="invalid_state",
            )

        # Validate replacement nominee (BR-EL-014)
        sub_leaves_qs = get_active_leaves_for_employee(new_substitute_id)
        sub_spans = [
            ExistingLeaveSpan(
                leave_id=sl.id,
                category=sl.leave_type.code,
                start_date=sl.start_date,
                end_date=sl.end_date,
                is_half_day=sl.is_half_day,
                half_day_period=sl.half_day_period,
            )
            for sl in sub_leaves_qs
        ]
        sub_res = check_substitute_eligibility(
            applicant_id=user_id,
            substitute_id=new_substitute_id,
            start_date=app.start_date,
            end_date=app.end_date,
            substitute_active_leaves=sub_spans,
            is_employee=True,
        )
        if not sub_res.is_valid:
            raise BadRequestError(sub_res.error_message, code=sub_res.error_code)

        from_status = app.status
        app.substitute_id = new_substitute_id
        app.substitute_status = "PENDING"
        app.substitute_declined_reason = ""
        app.substitute_responded_at = None
        app.status = "AWAITING_SUBSTITUTE"
        app.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action="REPLACE_SUBSTITUTE",
            from_status=from_status,
            to_status=app.status,
            remarks=f"Nominated replacement substitute #{new_substitute_id}.",
        )

    return app
