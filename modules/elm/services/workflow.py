"""Core ELM transitions. Every state change is validated and recorded atomically."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from modules.elm.models import LeaveRequest, LeavePolicy, LeaveAccount, LeaveTransaction


PENDING = {"awaiting_substitute_response", "applicant_action_required", "awaiting_unit_head_review", "awaiting_establishment_routing", "awaiting_final_sanction_decision", "awaiting_director_self_sanction"}

@transaction.atomic
def submit(*, actor, data):
    start, end = data["start_date"], data["end_date"]
    if end < start: raise ValidationError({"end_date":"End date must be on or after start date."})
    if start < timezone.localdate(): raise ValidationError({"start_date":"Leave cannot start in the past."})
    category = data["category"]
    policy = LeavePolicy.objects.filter(category=category, enabled=True).first()
    if policy is None: raise ValidationError({"category":"Leave category is not configured."})
    if LeaveRequest.objects.filter(user_id=actor.user_id, status__in=PENDING|{"approved","extension_pending"}, start_date__lte=end, end_date__gte=start).exists():
        raise ValidationError({"dates":"Leave overlaps an existing pending or approved request."})
    days = (end-start).days + 1
    substitute_id = data.get("substitute_user_id")
    if policy.requires_substitute and not substitute_id:
        raise ValidationError({"substitute_user_id":"A substitute is required for this leave category."})
    obj = LeaveRequest.objects.create(user_id=actor.user_id, category=category, start_date=start, end_date=end,
        days=days, purpose=data["purpose"], station_leave=data.get("station_leave",{}),
        substitute_user_id=substitute_id,
        status="awaiting_substitute_response" if policy.requires_substitute else "awaiting_unit_head_review")
    return obj

@transaction.atomic
def transition(*, request_obj, actor, action, reason=""):
    old = request_obj.status
    if action == "withdraw":
        if actor.user_id != request_obj.user_id or old not in PENDING: raise PermissionDenied("Only the applicant can withdraw a pending request.")
        request_obj.status = "withdrawn"
    elif action in ("accept_substitute", "decline_substitute"):
        if actor.user_id != request_obj.substitute_user_id or old != "awaiting_substitute_response": raise PermissionDenied("This substitute response is not assigned to you.")
        request_obj.substitute_decision = "accept" if action == "accept_substitute" else "decline"
        request_obj.status = "awaiting_unit_head_review" if action == "accept_substitute" else "applicant_action_required"
    elif action in ("approve", "not_recommended"):
        if old != "awaiting_unit_head_review": raise ValidationError("Request is not awaiting Unit Head review.")
        request_obj.unit_head_decision = action
        policy = LeavePolicy.objects.filter(category=request_obj.category).first()
        if policy and policy.higher_sanction:
            # Not recommended is a recommendation only; final authority still decides.
            request_obj.status = "awaiting_final_sanction_decision"
        else:
            request_obj.status = "approved" if action == "approve" else "rejected"
    elif action in ("final_approve", "final_reject"):
        if old not in ("awaiting_final_sanction_decision", "awaiting_director_self_sanction"): raise ValidationError("Request is not awaiting final sanction.")
        request_obj.final_decision = "approve" if action == "final_approve" else "reject"
        request_obj.status = "approved" if action == "final_approve" else "rejected"
    else:
        raise ValidationError({"action":"Unsupported workflow action."})
    request_obj.decision_reason = reason
    request_obj.version += 1
    request_obj.save(update_fields=["status","substitute_decision","unit_head_decision","final_decision","decision_reason","version","updated_at"])
    if request_obj.status == "approved":
        account, _ = LeaveAccount.objects.get_or_create(user_id=request_obj.user_id, category=request_obj.category, year=request_obj.start_date.year)
        LeaveTransaction.objects.create(account=account, request=request_obj, amount=-request_obj.days, transaction_type="leave_approved", actor_user_id=getattr(actor,"user_id",None))
        account.balance -= request_obj.days
        account.save(update_fields=["balance","updated_at"])
    return request_obj
