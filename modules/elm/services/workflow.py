from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from modules.elm.models import (
    LeaveRequest, LeaveBalance, LeaveSubstituteConsent, LeaveAction,
    LeaveCategory, LeaveStatus, PartOfDay
)
from modules.elm.services.calculation import validate_leave_application

def apply_for_leave(user_id: int, category: str, start_date, end_date, reason: str, part_of_day: str = 'full', substitute_user_id: int | None = None, station_leave: bool = False, station_destination: str = ''):
    with transaction.atomic():
        computed_days = validate_leave_application(user_id, category, start_date, end_date, part_of_day, substitute_user_id, station_leave, station_destination)
        has_substitute = substitute_user_id is not None
        initial_status = LeaveStatus.PENDING_SUBSTITUTE if has_substitute else LeaveStatus.PENDING_UNIT_HEAD
        sub_status = 'pending' if has_substitute else 'none'
        req = LeaveRequest.objects.create(
            user_id=user_id, category=category, start_date=start_date, end_date=end_date,
            part_of_day=part_of_day, computed_days=computed_days, reason=reason,
            station_leave=station_leave, station_destination=station_destination,
            substitute_user_id=substitute_user_id, substitute_status=sub_status,
            status=initial_status
        )
        if has_substitute:
            LeaveSubstituteConsent.objects.create(request=req, substitute_user_id=substitute_user_id, status='pending', is_current=True)
        bal = LeaveBalance.objects.get(user_id=user_id, year=start_date.year, category=category)
        bal.pending_days += computed_days
        bal.save(update_fields=['pending_days'])
        LeaveAction.objects.create(request=req, actor_user_id=user_id, action='submitted', note=reason)
    return req

def respond_substitute_consent(request_id: int, substitute_user_id: int, decision: str, note: str = ''):
    with transaction.atomic():
        req = LeaveRequest.objects.get(pk=request_id)
        if req.substitute_user_id != substitute_user_id or req.status != LeaveStatus.PENDING_SUBSTITUTE:
            raise ValidationError('Cannot respond to this substitute consent request.')
        consent = req.substitute_consents.filter(substitute_user_id=substitute_user_id, is_current=True).first()
        if not consent: raise ValidationError('No active consent record found.')
        if decision == 'accept':
            consent.status = 'accepted'; consent.response_note = note; consent.responded_at = timezone.now(); consent.save()
            req.substitute_status = 'accepted'; req.status = LeaveStatus.PENDING_UNIT_HEAD; req.save(update_fields=['substitute_status', 'status'])
            LeaveAction.objects.create(request=req, actor_user_id=substitute_user_id, action='substitute_accepted', note=note)
        elif decision == 'decline':
            consent.status = 'declined'; consent.response_note = note; consent.responded_at = timezone.now(); consent.save()
            req.substitute_status = 'declined'; req.status = LeaveStatus.SUBSTITUTE_DECLINED; req.save(update_fields=['substitute_status', 'status'])
            LeaveAction.objects.create(request=req, actor_user_id=substitute_user_id, action='substitute_declined', note=note)
        else: raise ValidationError('Decision must be accept or decline.')
    return req

def nominate_replacement_substitute(request_id: int, user_id: int, new_substitute_user_id: int):
    with transaction.atomic():
        req = LeaveRequest.objects.get(pk=request_id, user_id=user_id)
        if req.status != LeaveStatus.SUBSTITUTE_DECLINED: raise ValidationError('Can only replace substitute when previous substitute declined.')
        if new_substitute_user_id == user_id: raise ValidationError('Substitute cannot be applicant.')
        req.substitute_consents.filter(is_current=True).update(is_current=False)
        req.substitute_user_id = new_substitute_user_id
        req.substitute_status = 'pending'
        req.status = LeaveStatus.PENDING_SUBSTITUTE
        req.save(update_fields=['substitute_user_id', 'substitute_status', 'status'])
        LeaveSubstituteConsent.objects.create(request=req, substitute_user_id=new_substitute_user_id, status='pending', is_current=True)
        LeaveAction.objects.create(request=req, actor_user_id=user_id, action='replacement_substitute_nominated', note=f'Nominated substitute #{new_substitute_user_id}')
    return req

def review_unit_head(request_id: int, reviewer_user_id: int, decision: str, note: str = ''):
    with transaction.atomic():
        req = LeaveRequest.objects.get(pk=request_id)
        if req.status != LeaveStatus.PENDING_UNIT_HEAD: raise ValidationError('Request is not awaiting Unit Head review.')
        bal = LeaveBalance.objects.get(user_id=req.user_id, year=req.start_date.year, category=req.category)
        if req.category in [LeaveCategory.CL, LeaveCategory.RH]:
            # Unit Head is final authority
            if decision == 'approve':
                req.status = LeaveStatus.APPROVED; req.final_decision = 'approved'
                req.final_decision_by = reviewer_user_id; req.decision_date = timezone.now()
                req.final_decision_note = note
                bal.used_days += req.computed_days; bal.pending_days -= req.computed_days
                bal.save(update_fields=['used_days', 'pending_days'])
            elif decision == 'reject':
                req.status = LeaveStatus.REJECTED; req.final_decision = 'rejected'
                req.final_decision_by = reviewer_user_id; req.decision_date = timezone.now()
                req.final_decision_note = note
                bal.pending_days -= req.computed_days
                bal.save(update_fields=['pending_days'])
            else: raise ValidationError('Decision must be approve or reject.')
        else:
            # SCL, EL, COL, VL: Unit Head records recommendation
            if decision in ['recommended', 'not_recommended']:
                req.unit_head_recommendation = decision
                req.unit_head_note = note
                req.status = LeaveStatus.PENDING_SANCTION
            else: raise ValidationError('Decision must be recommended or not_recommended.')
        req.save()
        LeaveAction.objects.create(request=req, actor_user_id=reviewer_user_id, action=f'unit_head_{decision}', note=note)
    return req

def sanction_final_decision(request_id: int, sanctioner_user_id: int, decision: str, note: str = ''):
    with transaction.atomic():
        req = LeaveRequest.objects.get(pk=request_id)
        if req.status != LeaveStatus.PENDING_SANCTION: raise ValidationError('Request is not awaiting final sanction.')
        bal = LeaveBalance.objects.get(user_id=req.user_id, year=req.start_date.year, category=req.category)
        if decision == 'approve':
            req.status = LeaveStatus.APPROVED; req.final_decision = 'approved'
            req.final_decision_by = sanctioner_user_id; req.decision_date = timezone.now()
            req.final_decision_note = note
            bal.used_days += req.computed_days; bal.pending_days -= req.computed_days
            bal.save(update_fields=['used_days', 'pending_days'])
        elif decision == 'reject':
            req.status = LeaveStatus.REJECTED; req.final_decision = 'rejected'
            req.final_decision_by = sanctioner_user_id; req.decision_date = timezone.now()
            req.final_decision_note = note
            bal.pending_days -= req.computed_days
            bal.save(update_fields=['pending_days'])
        else: raise ValidationError('Decision must be approve or reject.')
        req.save()
        LeaveAction.objects.create(request=req, actor_user_id=sanctioner_user_id, action=f'sanction_{decision}', note=note)
    return req
