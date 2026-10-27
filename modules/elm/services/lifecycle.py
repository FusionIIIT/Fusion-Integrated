from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from modules.elm.models import (
    LeaveRequest, LeaveBalance, DutyResumption, LeaveAction,
    LeaveCategory, LeaveStatus
)

@transaction.atomic()
def withdraw_leave_request(request_id: int, user_id: int, reason: str = ''):
    req = LeaveRequest.objects.get(pk=request_id, user_id=user_id)
    if req.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED]:
        raise ValidationError('Cannot withdraw a request that is already finalized.')
    bal = LeaveBalance.objects.get(user_id=req.user_id, year=req.start_date.year, category=req.category)
    bal.pending_days -= req.computed_days
    bal.save(update_fields=['pending_days'])
    req.status = LeaveStatus.WITHDRAWN
    req.save(update_fields=['status'])
    LeaveAction.objects.create(request=req, actor_user_id=user_id, action='withdrawn', note=reason)
    return req

@transaction.atomic()
def request_cancellation(request_id: int, user_id: int, reason: str = ''):
    req = LeaveRequest.objects.get(pk=request_id, user_id=user_id)
    if req.status != LeaveStatus.APPROVED: raise ValidationError('Only approved leave can be cancelled.')
    if timezone.localdate() >= req.start_date: raise ValidationError('Cannot request cancellation after leave has already commenced.')
    req.status = LeaveStatus.CANCELLATION_REQUESTED
    req.save(update_fields=['status'])
    LeaveAction.objects.create(request=req, actor_user_id=user_id, action='cancellation_requested', note=reason)
    return req

@transaction.atomic()
def review_cancellation(request_id: int, reviewer_user_id: int, decision: str, note: str = ''):
    req = LeaveRequest.objects.get(pk=request_id)
    if req.status != LeaveStatus.CANCELLATION_REQUESTED: raise ValidationError('Request is not awaiting cancellation review.')
    bal = LeaveBalance.objects.get(user_id=req.user_id, year=req.start_date.year, category=req.category)
    if decision == 'approve':
        req.status = LeaveStatus.CANCELLED; req.final_decision = 'cancelled'
        bal.used_days -= req.computed_days  # restore balance
        bal.save(update_fields=['used_days'])
    elif decision == 'reject':
        req.status = LeaveStatus.APPROVED  # remains approved
    else: raise ValidationError('Decision must be approve or reject.')
    req.save()
    LeaveAction.objects.create(request=req, actor_user_id=reviewer_user_id, action=f'cancellation_{decision}', note=note)
    return req

@transaction.atomic()
def submit_duty_resumption(request_id: int, user_id: int, actual_resumption_date, reason: str = ''):
    req = LeaveRequest.objects.get(pk=request_id, user_id=user_id)
    if req.status != LeaveStatus.APPROVED: raise ValidationError('Can only submit resumption for approved leave.')
    expected_return = req.end_date + timedelta(days=1)
    if actual_resumption_date == expected_return:
        res_type = 'normal'; adj = Decimal('0')
    elif actual_resumption_date < expected_return:
        res_type = 'early'
        early_days = (expected_return - actual_resumption_date).days
        adj = -Decimal(str(early_days))  # negative adjustment to reduce used_days
    else:
        res_type = 'late'
        late_days = (actual_resumption_date - expected_return).days
        adj = Decimal(str(late_days))  # positive adjustment to add to used_days
    res_obj, created = DutyResumption.objects.update_or_create(
        request=req,
        defaults={
            'actual_resumption_date': actual_resumption_date,
            'resumption_type': res_type,
            'adjustment_days': adj,
            'reason': reason,
            'status': 'submitted'
        }
    )
    req.status = LeaveStatus.RESUMPTION_REQUESTED
    req.save(update_fields=['status'])
    LeaveAction.objects.create(request=req, actor_user_id=user_id, action='resumption_submitted', note=f'{res_type} resumption on {actual_resumption_date}')
    return res_obj

@transaction.atomic()
def review_duty_resumption(resumption_id: int, reviewer_user_id: int, decision: str, note: str = ''):
    res_obj = DutyResumption.objects.get(pk=resumption_id)
    req = res_obj.request
    bal = LeaveBalance.objects.get(user_id=req.user_id, year=req.start_date.year, category=req.category)
    if decision == 'approve':
        res_obj.status = 'approved'; res_obj.reviewed_by = reviewer_user_id
        req.status = LeaveStatus.APPROVED
        if res_obj.adjustment_days != Decimal('0'):
            bal.used_days += res_obj.adjustment_days
            bal.save(update_fields=['used_days'])
    elif decision == 'reject':
        res_obj.status = 'rejected'; res_obj.reviewed_by = reviewer_user_id
        req.status = LeaveStatus.APPROVED
    else: raise ValidationError('Decision must be approve or reject.')
    res_obj.save(); req.save()
    LeaveAction.objects.create(request=req, actor_user_id=reviewer_user_id, action=f'resumption_{decision}', note=note)
    return res_obj

@transaction.atomic()
def process_year_end(year: int):
    LeaveBalance.objects.filter(year=year, category__in=[LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL]).update(pending_days=0)
    vl_balances = LeaveBalance.objects.filter(year=year, category=LeaveCategory.VL)
    next_year = year + 1
    for vl in vl_balances:
        unused_vl = vl.available_days
        if unused_vl > 0:
            converted_el = unused_vl * Decimal('0.5')
            el_next, _ = LeaveBalance.objects.get_or_create(
                user_id=vl.user_id, year=next_year, category=LeaveCategory.EL,
                defaults={'entitled_days': Decimal('0'), 'used_days': Decimal('0'), 'pending_days': Decimal('0')}
            )
            el_next.entitled_days += converted_el
            el_next.save(update_fields=['entitled_days'])
