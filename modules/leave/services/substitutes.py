"""Substitute response and replacement services (EL-UC-002, EL-UC-019)."""

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.entities import LeaveStatus, SubstituteStatus
from modules.leave.domain.errors import DomainError
from modules.leave.domain.rules import validate_substitute_eligibility
from modules.leave.models import (
    LeaveActionLog,
    LeaveApplication,
    LeaveBalance,
    LeaveHierarchyConfig,
)


def respond_substitute(
    application_id: int,
    principal,
    accept: bool,
    remarks: str = "",
) -> LeaveApplication:
    """Substitute accepts or declines responsibility (EL-UC-002, BW-EL-08)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.substitute_user_id != principal.user_id:
            raise ConflictError("You are not the nominated substitute for this request.")

        if app.status != LeaveStatus.AWAITING_SUBSTITUTE.value:
            raise ConflictError("This application is not currently awaiting substitute response.")

        from_status = app.status
        app.substitute_remarks = remarks

        if accept:
            app.substitute_status = SubstituteStatus.ACCEPTED.value
            # Check if applicant is Director (BW-EL-08: Director self-sanction with substitute)
            is_applicant_director = LeaveHierarchyConfig.objects.filter(
                director_user_id=app.applicant_user_id
            ).exists()

            if is_applicant_director:
                next_status = LeaveStatus.APPROVED.value
                app.status = next_status
                # Deduct balance immediately
                bal = LeaveBalance.objects.select_for_update().get(
                    user_id=app.applicant_user_id,
                    year=app.start_date.year,
                    leave_type=app.leave_type,
                )
                bal.balance -= app.days_count
                bal.availed += app.days_count
                bal.save(update_fields=["balance", "availed", "updated_at"])
                action_name = "DIRECTOR_SELF_SANCTION_APPROVED"
                action_remarks = remarks or "Substitute accepted; Director self-sanction completed"
            else:
                next_status = LeaveStatus.AWAITING_UNIT_HEAD.value
                app.status = next_status
                action_name = "SUBSTITUTE_ACCEPT"
                action_remarks = remarks or "Substitute accepted responsibility"

            app.save(
                update_fields=["substitute_status", "substitute_remarks", "status", "updated_at"]
            )
            LeaveActionLog.objects.create(
                application=app,
                actor_user_id=principal.user_id,
                action=action_name,
                from_status=from_status,
                to_status=next_status,
                remarks=action_remarks,
            )
        else:
            app.substitute_status = SubstituteStatus.DECLINED.value
            next_status = LeaveStatus.SUBSTITUTE_DECLINED.value
            app.status = next_status
            app.save(
                update_fields=["substitute_status", "substitute_remarks", "status", "updated_at"]
            )
            LeaveActionLog.objects.create(
                application=app,
                actor_user_id=principal.user_id,
                action="SUBSTITUTE_DECLINE",
                from_status=from_status,
                to_status=next_status,
                remarks=remarks or "Substitute declined responsibility",
            )

        return app


def replace_substitute(
    application_id: int,
    principal,
    new_substitute_id: int,
) -> LeaveApplication:
    """Nominate replacement substitute after decline (EL-UC-019)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.applicant_user_id != principal.user_id:
            raise ConflictError("Only the applicant can nominate a replacement substitute.")

        if app.status != LeaveStatus.SUBSTITUTE_DECLINED.value:
            raise ConflictError(
                "Replacement can only be nominated when status is SUBSTITUTE_DECLINED."
            )

        sub_leaves = list(
            LeaveApplication.objects.filter(
                applicant_user_id=new_substitute_id,
                status="APPROVED",
            ).values_list("start_date", "end_date")
        )
        try:
            validate_substitute_eligibility(
                applicant_user_id=principal.user_id,
                substitute_user_id=new_substitute_id,
                substitute_active_leaves=sub_leaves,
                requested_start=app.start_date,
                requested_end=app.end_date,
            )
        except DomainError as e:
            raise ConflictError(e.message) from None

        from_status = app.status
        app.substitute_user_id = new_substitute_id
        app.substitute_status = SubstituteStatus.PENDING.value
        app.status = LeaveStatus.AWAITING_SUBSTITUTE.value
        app.save(update_fields=["substitute_user_id", "substitute_status", "status", "updated_at"])

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="REPLACE_SUBSTITUTE",
            from_status=from_status,
            to_status=LeaveStatus.AWAITING_SUBSTITUTE.value,
            remarks=f"Nominated replacement substitute #{new_substitute_id}",
        )

        return app
