from django.db import transaction
from modules.leave.models import SubstituteRequest, LeaveApplication, LeaveActionHistory

@transaction.atomic
def respond_to_substitute_request(substitute_user_id: int, request_id: int, decision: str, remarks: str = "") -> SubstituteRequest:
    request = SubstituteRequest.objects.get(id=request_id)
    application = request.application
    
    if decision == "accepted":
        request.status = "accepted"
        if application.user.role == "director":
            application.status = "approved"
        else:
            application.status = "under_review"
    elif decision == "declined":
        request.status = "declined"
        application.status = "substitute_declined"
    
    request.remarks = remarks
    request.save()
    application.save()
    
    LeaveActionHistory.objects.create(
        user=substitute_user_id,
        action_type=decision,
        substitute_request=request,
        remarks=remarks
    )
    
    return request

@transaction.atomic
def nominate_replacement_substitute(user_id: int, application_id: int, new_substitute_user_id: int, responsibilities: str = "") -> SubstituteRequest:
    application = LeaveApplication.objects.get(id=application_id)
    
    if application.user.id != user_id or application.status != "substitute_declined":
        raise ValueError("Invalid request")
    
    new_request = SubstituteRequest.objects.create(
        application=application,
        substitute_user_id=new_substitute_user_id,
        responsibilities=responsibilities
    )
    
    application.status = "substitute_pending"
    application.save()
    
    LeaveActionHistory.objects.create(
        user=user_id,
        action_type="nomination",
        substitute_request=new_request,
        remarks=responsibilities
    )
    
    return new_request