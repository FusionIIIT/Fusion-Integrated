from django.db import transaction
from django.utils import timezone

from modules.elm.domain.validation import validate_leave_request
from modules.elm.models import LeaveApplication, LeaveBalance, SubstituteNominee


def create_leave_application(
    user,
    leave_type,
    start_date,
    end_date,
    is_half_day,
    current_balance,
    existing_leaves,
    half=None,
    substitute_user_id: int | None = None,
) -> LeaveApplication:
    is_valid, error_message = validate_leave_request(
        leave_type.code,
        start_date,
        end_date,
        is_half_day,
        current_balance,
        existing_leaves,
        half,
    )
    if not is_valid:
        raise ValueError(error_message)

    if substitute_user_id is not None and substitute_user_id == user.user_id:
        raise ValueError("Substitute cannot be the applicant")

    with transaction.atomic():
        application = LeaveApplication.objects.create(
            user=user,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            status=LeaveApplication.Status.DRAFT,
            reason="",
        )

        if substitute_user_id is not None:
            SubstituteNominee.objects.create(
                leave_application=application,
                user_id=substitute_user_id,
                status=SubstituteNominee.NominationStatus.PENDING,
            )
            application.status = LeaveApplication.Status.AWAITING_SUBSTITUTE_RESPONSE
        else:
            application.status = LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW

        application.save()

    return application


def respond_to_substitute_request(
    nominee_id: int, user_id: int, response: str
) -> dict:
    try:
        with transaction.atomic():
            nominee = SubstituteNominee.objects.get(id=nominee_id)
            if nominee.user_id != user_id:
                return {"success": False, "message": "Invalid user for this nomination"}
            if nominee.status != SubstituteNominee.NominationStatus.PENDING:
                return {"success": False, "message": "Nomination is not pending"}

            application = nominee.leave_application
            if response == "accepted":
                nominee.status = SubstituteNominee.NominationStatus.ACCEPTED
                application.status = LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW
            elif response == "declined":
                nominee.status = SubstituteNominee.NominationStatus.DECLINED
                application.status = LeaveApplication.Status.APPLICANT_ACTION_REQUIRED
            else:
                return {"success": False, "message": "Invalid response"}

            nominee.save()
            application.save()

            return {"success": True, "message": "Response processed successfully"}
    except SubstituteNominee.DoesNotExist:
        return {"success": False, "message": "Nomination not found"}


def unit_head_review(
    application_id: int,
    unit_head_user_id: int,
    decision: str,
    recommendation: str = "",
) -> dict:
    try:
        with transaction.atomic():
            application = LeaveApplication.objects.get(id=application_id)

            if application.status != LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW:
                return {
                    "success": False,
                    "message": "Application is not in the correct state for unit head review"
                }

            if not unit_head_user_id or unit_head_user_id == application.user_id:
                return {"success": False, "message": "Invalid unit head user"}

            if application.leave_type.code in ['CL', 'RH']:
                if decision == "approved":
                    application.status = LeaveApplication.Status.APPROVED
                elif decision == "rejected":
                    application.status = LeaveApplication.Status.REJECTED
                else:
                    return {"success": False, "message": "Invalid decision"}
            else:
                application.unit_head_recommendation = recommendation
                application.status = LeaveApplication.Status.AWAITING_FINAL_SANCTION_DECISION

            application.save()
            return {"success": True, "message": "Unit head review processed successfully"}

    except LeaveApplication.DoesNotExist:
        return {"success": False, "message": "Application not found"}


def approve_leave_application(
    application_id: int,
    approver_user_id: int
) -> dict:
    try:
        with transaction.atomic():
            application = LeaveApplication.objects.get(id=application_id)

            if application.status not in [
                LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW,
                LeaveApplication.Status.AWAITING_FINAL_SANCTION_DECISION,
            ]:
                return {
                    "success": False,
                    "message": "Application is not in a state to be approved"
                }

            requested = (
                0.5 if getattr(application, 'is_half_day', False)
                else (application.end_date - application.start_date).days + 1
            )

            user_leave_balance = LeaveBalance.objects.get(
                user=application.user,
                leave_type=application.leave_type
            )
            user_leave_balance.balance -= requested
            user_leave_balance.save()

            application.status = LeaveApplication.Status.APPROVED
            application.final_decision = 'approved'
            application.final_decision_date = timezone.now()
            application.save()

            return {"success": True, "message": "Application approved successfully"}

    except LeaveApplication.DoesNotExist:
        return {"success": False, "message": "Application not found"}
    except LeaveBalance.DoesNotExist:
        return {"success": False, "message": "Leave balance not found"}


def nominate_replacement_substitute(
    application_id: int,
    applicant_user_id: int,
    new_substitute_user_id: int
) -> dict:
    try:
        with transaction.atomic():
            application = LeaveApplication.objects.get(id=application_id)

            if application.user_id != applicant_user_id:
                return {
                    "success": False,
                    "message": "Only the applicant can nominate a replacement"
                }

            if application.status != LeaveApplication.Status.APPLICANT_ACTION_REQUIRED:
                return {
                    "success": False,
                    "message": "Application is not in the correct state for replacement"
                }

            if new_substitute_user_id == applicant_user_id:
                return {"success": False, "message": "Substitute cannot be the applicant"}

            SubstituteNominee.objects.create(
                leave_application=application,
                user_id=new_substitute_user_id,
                status=SubstituteNominee.NominationStatus.PENDING,
            )
            application.status = LeaveApplication.Status.AWAITING_SUBSTITUTE_RESPONSE
            application.save()

            return {"success": True, "message": "Replacement substitute nominated successfully"}

    except LeaveApplication.DoesNotExist:
        return {"success": False, "message": "Application not found"}
