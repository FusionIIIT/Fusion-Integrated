
from django.db import transaction

from django.utils import timezone

from .models import LeaveRequest, LeaveBalance, SubstituteAssignment, LeaveAuditTrail

from .domain.counting import calculate_leave_days

from .domain.state_machine import get_valid_transitions, LeaveStatus





def apply_for_leave(applicant_user_id, leave_type_id, start_date, end_date, category):

    leave_type = LeaveType.objects.get(id=leave_type_id)

    leave_request = LeaveRequest(

        applicant_user_id=applicant_user_id,

        leave_type=leave_type,

        start_date=start_date,

        end_date=end_date,

        status=LeaveStatus.DRAFT.value

    )

    leave_request.save()



    leave_balance = LeaveBalance.objects.get(user_id=applicant_user_id,
calendar_year=timezone.now().year, category=category)

    leave_days = calculate_leave_days(start_date, end_date, category)

    if leave_days > leave_balance.credited - leave_balance.availed:

        raise ValueError("Insufficient leave balance")



    leave_request.status = LeaveStatus.AWAITING_SUBSTITUTE.value

    leave_request.save()



    LeaveAuditTrail.objects.create(

        leave_request=leave_request,

        actor_user_id=applicant_user_id,

        from_status=LeaveStatus.DRAFT.value,

        to_status=LeaveStatus.AWAITING_SUBSTITUTE.value,

        action="Applied for leave",

        comments=f"Leave type: {leave_type.name}, Days: {leave_days}"

    )



    return leave_request





def respond_to_substitute(assignment_id, user_id, accept):

    assignment = SubstituteAssignment.objects.get(id=assignment_id)

    leave_request = assignment.leave_request



    if accept:

        leave_request.status = LeaveStatus.AWAITING_UNIT_HEAD.value

        leave_request.save()

        LeaveAuditTrail.objects.create(

            leave_request=leave_request,

            actor_user_id=user_id,

            from_status=LeaveStatus.AWAITING_SUBSTITUTE.value,

            to_status=LeaveStatus.AWAITING_UNIT_HEAD.value,

            action="Accepted substitute assignment",

            comments=f"Substitute: {user_id}"

        )

    else:

        leave_request.status = LeaveStatus.APPLICANT_ACTION_REQUIRED.value

        leave_request.save()

        LeaveAuditTrail.objects.create(

            leave_request=leave_request,

            actor_user_id=user_id,

            from_status=LeaveStatus.AWAITING_SUBSTITUTE.value,

            to_status=LeaveStatus.APPLICANT_ACTION_REQUIRED.value,

            action="Declined substitute assignment",

            comments=f"Substitute: {user_id}"

        )



    return leave_request





def review_unit_head(request_id, reviewer_id, decision):

    leave_request = LeaveRequest.objects.get(id=request_id)

    valid_transitions = get_valid_transitions(leave_request.status,
['leave_management.unit_head.review'])



    if decision == 'approve':

        if leave_request.leave_type.category in ['CL', 'RH']:

            leave_request.status = LeaveStatus.APPROVED.value

        else:

            leave_request.status = LeaveStatus.AWAITING_UNIT_HEAD.value

        leave_request.save()

        LeaveAuditTrail.objects.create(

            leave_request=leave_request,

            actor_user_id=reviewer_id,

            from_status=leave_request.status,

            to_status=leave_request.status,

            action="Reviewed leave request",

            comments=f"Decision: {decision}"

        )

    elif decision == 'reject':

        leave_request.status = LeaveStatus.REJECTED.value

        leave_request.save()

        LeaveAuditTrail.objects.create(

            leave_request=leave_request,

            actor_user_id=reviewer_id,

            from_status=leave_request.status,

            to_status=leave_request.status,

            action="Reviewed leave request",

            comments=f"Decision: {decision}"

        )



    return leave_request





def withdraw_pending_request(request_id, user_id):

    leave_request = LeaveRequest.objects.get(id=request_id)

    if leave_request.status in [LeaveStatus.DRAFT.value, LeaveStatus.AWAITING_SUBSTITUTE.value]:        

        leave_request.status = LeaveStatus.CANCELLED.value

        leave_request.save()

        LeaveAuditTrail.objects.create(

            leave_request=leave_request,

            actor_user_id=user_id,

            from_status=leave_request.status,

            to_status=leave_request.status,

            action="Withdrawn pending leave request",

            comments="Request withdrawn by user"

        )                                                                                               
                                                                                                        
    else:
                                                                                                        
        raise ValueError("Cannot withdraw a non-pending request")
                                                                                                        
                                                                                                        

    return leave_request
