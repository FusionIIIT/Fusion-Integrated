from __future__ import annotations
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Optional

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.directory.contracts import get_users, UserDTO
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, LeaveTransaction,
    WorkflowTask, SLAEventLog, ResumptionRecord, OrganizationalUnit,
    HolidayCalendar, VacationPeriod, LeaveHierarchy, LeaveHierarchyStep,
    LeavePolicy
)
from modules.leave_elm.domain.policy import (
    LeaveCategory, HolidayCalendar as PolicyCalendar,
    VacationPeriod as PolicyVacationPeriod, LeavePolicy as DomainPolicy
)

def _get_policy() -> DomainPolicy:
    db_policy = LeavePolicy.objects.first()
    if not db_policy:
        return DomainPolicy()
    return DomainPolicy(
        cl_days=db_policy.CL_DAYS, rh_days=db_policy.RH_DAYS,
        scl_max_days=db_policy.SCL_MAX_DAYS, el_days=db_policy.EL_DAYS,
        col_days=db_policy.COL_DAYS, vl_days=db_policy.VL_DAYS,
        vl_to_el_ratio=db_policy.VL_TO_EL_RATIO
    )

def _get_calendar() -> PolicyCalendar:
    effective = HolidayCalendar.objects.filter(is_effective=True).first()
    if not effective:
        return PolicyCalendar(year=2025, holidays=[], restricted_holidays=[], is_effective=False)
    hols = list(effective.holidays.all().values_list('date', flat=True))
    rh = list(effective.holidays.filter(type='RH').values_list('date', flat=True))
    return PolicyCalendar(
        year=effective.year, holidays=hols, restricted_holidays=rh,
        is_effective=effective.is_effective
    )

def _get_vacation_periods() -> list[PolicyVacationPeriod]:
    periods = VacationPeriod.objects.filter(year=date.today().year)
    return [PolicyVacationPeriod(
        year=p.year, start_date=p.start_date, end_date=p.end_date, name=p.name
    ) for p in periods]

def _get_unit_head(user_id: int) -> Optional[int]:
    unit = OrganizationalUnit.objects.filter(unit_head_user_id=user_id).first()
    return unit.unit_head_user_id if unit else None

def _is_director(user_id: int) -> bool:
    return user_id == 1000  # Assumed Director ID

def _get_sanctioning_path(category: str, user_id: int) -> list[int]:
    """Return ordered list of user IDs for sanctioning path."""
    policy = _get_policy()
    if category in ('CL', 'RH'):
        unit_head = _get_unit_head(user_id)
        return [unit_head] if unit_head else []
    # Higher sanction
    steps = LeaveHierarchy.objects.first()
    if not steps:
        return []
    path = []
    for step in steps.steps.all():
        if step.is_establishment_step:
            continue
        role_users = OrganizationalUnit.objects.filter(
            unit_head_user_id__in=[step.role_code] if step.role_code.isdigit() else []
        ).values_list('unit_head_user_id', flat=True)
        path.extend(role_users)
    return path

def _validate_leave_request(
    user_id: int, category: str, start_date: date, end_date: date,
    substitute_user_id: Optional[int] = None
) -> tuple[bool, list[str]]:
    errors = []
    policy = _get_policy()
    calendar = _get_calendar()
    periods = _get_vacation_periods()
    
    if category not in ('CL', 'RH', 'SCL', 'EL', 'COL', 'VL'):
        errors.append(f"Invalid category: {category}")
        return False, errors
    
    # Check entitlement
    if category == 'RH':
        if start_date not in calendar.restricted_holidays:
            errors.append("Restricted Holiday must match published RH calendar")
            return False, errors
    elif category == 'VL':
        if not any(p.contains_date(start_date) for p in periods):
            errors.append("VL must be within a vacation period")
            return False, errors
    
    # Check balance
    balances = LeaveBalance.objects.filter(user_id=user_id).order_by('-effective_date')
    latest = balances.first()
    if not latest:
        errors.append("No leave balance record found")
        return False, errors
    
    if category == 'CL':
        if latest.cl_balance < Decimal('0.5'):
            errors.append("Insufficient CL balance")
    elif category == 'RH':
        if latest.rh_balance < Decimal('1'):
            errors.append("Insufficient RH balance")
    elif category == 'SCL':
        if latest.scl_balance < Decimal('1'):
            errors.append("Insufficient SCL balance")
    elif category == 'EL':
        if latest.el_balance < Decimal('1'):
            errors.append("Insufficient EL balance")
    elif category == 'COL':
        if latest.col_balance < Decimal('1'):
            errors.append("Insufficient COL balance")
    elif category == 'VL':
        if latest.vl_balance < Decimal('2'):  # 2 VL = 1 EL
            errors.append("Insufficient VL balance")
    
    # Check overlap
    existing = LeaveApplication.objects.filter(
        user_id=user_id, status__in=('APPROVED', 'AWAITING_SUBSTITUTE', 'AWAITING_UNIT_HEAD',
                                     'AWAITING_ESTABLISHMENT', 'AWAITING_FINAL_SANCTION'),
        start_date__lte=end_date, end_date__gte=start_date
    ).exclude(
        id__in=LeaveApplication.objects.filter(
            user_id=user_id, status='DRAFT'
        ).values_list('id', flat=True)
    )
    
    if existing.exists():
        errors.append("Overlaps with active pending or approved leave")
        return False, errors
    
    # Check substitute overlap
    if substitute_user_id:
        sub_exists = LeaveApplication.objects.filter(
            user_id=substitute_user_id, status__in=('APPROVED', 'AWAITING_SUBSTITUTE',
                                                     'AWAITING_UNIT_HEAD', 'AWAITING_ESTABLISHMENT',
                                                     'AWAITING_FINAL_SANCTION'),
            start_date__lte=end_date, end_date__gte=start_date
        ).exists()
        if sub_exists:
            errors.append("Substitute has overlapping leave")
    
    return len(errors) == 0, errors

def _check_substitute_consent(substitute_user_id: int) -> bool:
    """Check if substitute has accepted."""
    # In real impl, this would check a consent table or workflow task state
    # For now, assume we need to create the task and wait for response
    return True  # Placeholder - actual implementation needs consent tracking

def _create_application(
    user_id: int, category: str, start_date: date, end_date: date,
    purpose: str, station_leave_required: bool = False,
    substitute_user_id: Optional[int] = None
) -> LeaveApplication:
    """Create a new leave application."""
    policy = _get_policy()
    
    # Determine category-specific entitlement
    if category == 'CL':
        days = Decimal('0.5') if (start_date.day % 2 != 0 and end_date.day % 2 != 0) else Decimal('1')
    elif category == 'RH':
        days = Decimal('1')
    elif category == 'SCL':
        days = Decimal('1')
    elif category == 'EL':
        days = Decimal('1')
    elif category == 'COL':
        days = Decimal('1')
    elif category == 'VL':
        days = Decimal('2')  # 2 VL per day
    
    app = LeaveApplication.objects.create(
        user_id=user_id, category=category, start_date=start_date,
        end_date=end_date, purpose=purpose,
        station_leave_required=station_leave_required,
        substitute_user_id=substitute_user_id,
        created_by_user_id=user_id
    )
    
    # Determine initial status
    if substitute_user_id:
        app.status = 'AWAITING_SUBSTITUTE'
    elif _is_director(user_id):
        app.status = 'AWAITING_UNIT_HEAD'  # Director self-sanction starts at Unit Head
    else:
        app.status = 'AWAITING_UNIT_HEAD'
    
    app.save()
    return app

def _process_substitute_response(
    application_id: int, substitute_user_id: int, accepted: bool,
    new_substitute_user_id: Optional[int] = None
) -> tuple[bool, str]:
    """Process substitute response. Returns (success, message)."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if not app.substitute_user_id:
        return False, "No substitute nominated"
    
    if accepted:
        app.status = 'AWAITING_UNIT_HEAD'
        app.save()
        return True, "Substitute accepted"
    else:
        # Decline - allow replacement or withdrawal
        if new_substitute_user_id:
            app.substitute_user_id = new_substitute_user_id
            app.status = 'AWAITING_SUBSTITUTE'
            app.save()
            return True, "New substitute nominated"
        return False, "Substitute declined - must nominate replacement or withdraw"

def _route_to_sanctioning(app: LeaveApplication) -> WorkflowTask:
    """Route application to appropriate sanctioning authority."""
    policy = _get_policy()
    
    if app.category in ('CL', 'RH'):
        # Unit Head final decision
        unit_head_id = _get_unit_head(app.user_id)
        if not unit_head_id:
            raise ConflictError("No Unit Head configured")
        
        task = WorkflowTask.objects.create(
            application=app, task_type='UNIT_HEAD_REVIEW',
            assigned_to_user_id=unit_head_id, role_code='unit_head'
        )
        return task
    else:
        # Higher sanction path
        steps = _get_sanctioning_path(app.category, app.user_id)
        if not steps:
            raise ConflictError("No sanctioning path configured")
        
        task = WorkflowTask.objects.create(
            application=app, task_type='FINAL_SANCTION',
            assigned_to_user_id=steps[0], role_code='sanctioning_authority'
        )
        return task

def _make_final_decision(
    application_id: int, decision: Literal['APPROVED', 'REJECTED'],
    user_id: int
) -> tuple[bool, str]:
    """Make final sanctioning decision."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status not in ('AWAITING_FINAL_SANCTION', 'AWAITING_UNIT_HEAD'):
        return False, "Application not in sanctionable state"
    
    with transaction.atomic():
        # Update application
        app.final_decision_user_id = user_id
        app.final_decision_date = date.today()
        app.final_decision_type = decision
        
        if decision == 'APPROVED':
            app.status = 'APPROVED'
            
            # Deduct balance
            balances = LeaveBalance.objects.filter(user_id=app.user_id).order_by('-effective_date')
            latest = balances.first()
            
            if app.category == 'CL':
                days = Decimal('0.5') if (app.start_date.day % 2 != 0 and app.end_date.day % 2 != 0) else Decimal('1')
            elif app.category == 'RH':
                days = Decimal('1')
            elif app.category == 'SCL':
                days = Decimal('1')
            elif app.category == 'EL':
                days = Decimal('1')
            elif app.category == 'COL':
                days = Decimal('1')
            elif app.category == 'VL':
                days = Decimal('2')
            
            new_balance = getattr(latest, f'{app.category.lower()}_balance', Decimal('0')) - days
            
            # Create transaction record
            LeaveTransaction.objects.create(
                application=app, user_id=app.user_id,
                transaction_type='APPROVAL', category=app.category,
                quantity=days, balance_before=new_balance + days,
                balance_after=new_balance, processed_by_user_id=user_id
            )
            
            # Update balance
            latest.__setattr__(f'{app.category.lower()}_balance', new_balance)
            latest.save()
        else:
            app.status = 'REJECTED'
        
        app.save()
    
    return True, "Decision recorded"

def _withdraw_application(application_id: int, user_id: int) -> tuple[bool, str]:
    """Withdraw a pending application."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status == 'WITHDRAWN':
        return False, "Already withdrawn"
    
    if app.status in ('APPROVED', 'REJECTED'):
        return False, "Cannot withdraw approved/rejected application"
    
    with transaction.atomic():
        app.status = 'WITHDRAWN'
        app.withdrawn_by_user_id = user_id
        app.save()
    
    # Cancel associated tasks
    WorkflowTask.objects.filter(application=app).update(status='COMPLETED')
    
    return True, "Application withdrawn"

def _cancel_approved_leave(
    application_id: int, decision: Literal['APPROVED', 'REJECTED'],
    user_id: int
) -> tuple[bool, str]:
    """Cancel an approved leave before start."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status != 'APPROVED':
        return False, "Only approved leaves can be cancelled"
    
    if app.start_date <= date.today():
        return False, "Cannot cancel leave that has already started"
    
    with transaction.atomic():
        # Process through hierarchy
        if app.category in ('CL', 'RH'):
            unit_head_id = _get_unit_head(app.user_id)
            if not unit_head_id:
                raise ConflictError("No Unit Head configured")
            task = WorkflowTask.objects.create(
                application=app, task_type='UNIT_HEAD_REVIEW',
                assigned_to_user_id=unit_head_id, role_code='unit_head'
            )
        else:
            steps = _get_sanctioning_path(app.category, app.user_id)
            if not steps:
                raise ConflictError("No sanctioning path configured")
            task = WorkflowTask.objects.create(
                application=app, task_type='FINAL_SANCTION',
                assigned_to_user_id=steps[0], role_code='sanctioning_authority'
            )
        
        # Make final decision
        success, msg = _make_final_decision(app.id, decision, user_id)
        if not success:
            return False, msg
    
    return True, "Cancellation processed"

def _extend_ongoing_leave(
    application_id: int, additional_days: Decimal, user_id: int,
    substitute_user_id: Optional[int] = None
) -> tuple[bool, str]:
    """Extend an ongoing leave."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.category not in ('EL', 'COL', 'VL'):
        return False, "Extension only available for EL, COL, VL"
    
    if app.status != 'APPROVED':
        return False, "Only approved leaves can be extended"
    
    # Validate extension
    valid, errors = _validate_leave_request(
        user_id, app.category, app.end_date + timedelta(days=1),
        app.end_date + timedelta(days=int(additional_days)),
        substitute_user_id
    )
    if not valid:
        return False, "; ".join(errors)
    
    with transaction.atomic():
        # Create extension application linked to original
        ext_app = LeaveApplication.objects.create(
            user_id=app.user_id, category=app.category,
            start_date=app.end_date + timedelta(days=1),
            end_date=app.end_date + timedelta(days=int(additional_days)),
            purpose=f"Extension of {app.category} leave",
            station_leave_required=app.station_leave_required,
            substitute_user_id=substitute_user_id,
            created_by_user_id=user_id,
            original_application_id=app.id
        )
        
        ext_app.status = 'AWAITING_SUBSTITUTE' if substitute_user_id else 'AWAITING_UNIT_HEAD'
        ext_app.extension_incremental_days = additional_days
        ext_app.save()
    
    return True, "Extension request created"

def _submit_resumption(
    application_id: int, actual_date: date, user_id: int
) -> tuple[bool, str]:
    """Submit resumption of duty."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.category not in ('EL', 'COL', 'VL'):
        return False, "Resumption only for EL, COL, VL"
    
    if app.status != 'APPROVED':
        return False, "Only approved leaves can have resumption submitted"
    
    with transaction.atomic():
        record = ResumptionRecord.objects.create(
            application=app, user_id=user_id,
            actual_resumption_date=actual_date,
            reviewed_by_user_id=user_id
        )
        
        # Calculate adjustment
        approved_days = (app.end_date - app.start_date).days + 1
        actual_days = (actual_date - app.start_date).days + 1
        adjustment = Decimal(actual_days) - Decimal(approved_days)
        
        record.balance_adjustment = adjustment
        record.save()
    
    return True, "Resumption submitted"

def _record_offline_sanction(
    user_id: int, category: str, start_date: date, end_date: date,
    reference_number: str, evidence: str
) -> tuple[bool, str]:
    """Record offline-sanctioned leave."""
    with transaction.atomic():
        app = LeaveApplication.objects.create(
            user_id=user_id, category=category, start_date=start_date,
            end_date=end_date, purpose="Offline sanctioned",
            station_leave_required=False,
            created_by_user_id=user_id
        )
        
        # Calculate days
        if category == 'CL':
            days = Decimal('0.5') if (start_date.day % 2 != 0 and end_date.day % 2 != 0) else Decimal('1')
        elif category in ('RH', 'SCL', 'EL', 'COL', 'VL'):
            days = Decimal('1') if category != 'VL' else Decimal('2')
        
        # Create transaction
        LeaveTransaction.objects.create(
            application=app, user_id=user_id,
            transaction_type='APPROVAL', category=category,
            quantity=days, balance_before=Decimal('0'),
            balance_after=-days, processed_by_user_id=user_id
        )
    
    return True, "Offline sanction recorded"

def _maintain_leave_record(
    user_id: int, application_id: int, field: str, value
) -> tuple[bool, str]:
    """Maintain or correct a leave record within authorized scope."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status in ('APPROVED', 'REJECTED'):
        return False, "Cannot modify approved/rejected applications"
    
    allowed_fields = ['purpose', 'station_leave_required']
    if field not in allowed_fields:
        return False, f"Field {field} not allowed for maintenance"
    
    with transaction.atomic():
        setattr(app, field, value)
        app.save()
    
    return True, "Record maintained"

def _get_leave_balances(user_id: int) -> dict:
    """Get current leave balances."""
    balances = LeaveBalance.objects.filter(user_id=user_id).order_by('-effective_date')
    latest = balances.first()
    
    if not latest:
        return {
            'cl_balance': Decimal('0'), 'rh_balance': Decimal('0'),
            'scl_balance': Decimal('0'), 'el_balance': Decimal('0'),
            'col_balance': Decimal('0'), 'vl_balance': Decimal('0')
        }
    
    return {
        'cl_balance': latest.cl_balance, 'rh_balance': latest.rh_balance,
        'scl_balance': latest.scl_balance, 'el_balance': latest.el_balance,
        'col_balance': latest.col_balance, 'vl_balance': latest.vl_balance
    }

def _get_leave_history(user_id: int) -> list:
    """Get leave application history."""
    apps = LeaveApplication.objects.filter(user_id=user_id).order_by('-created_at')
    
    history = []
    for app in apps:
        entry = {
            'id': app.id, 'category': app.category,
            'start_date': app.start_date, 'end_date': app.end_date,
            'purpose': app.purpose, 'status': app.status,
            'created_at': app.created_at
        }
        
        if app.final_decision_type:
            entry['final_decision'] = app.final_decision_type
            entry['decision_date'] = app.final_decision_date
        
        history.append(entry)
    
    return history

def _process_year_end(user_id: int) -> dict:
    """Process year-end leave account."""
    policy = _get_policy()
    today = date.today()
    year_end = date(today.year, 12, 31)
    
    results = {
        'processed': False, 'exceptions': [],
        'lapses': [], 'conversions': [], 'carry_forwards': []
    }
    
    balances = LeaveBalance.objects.filter(user_id=user_id, effective_date__lte=year_end)
    latest = balances.first()
    
    if not latest:
        return results
    
    # Process CL, RH, SCL - lapse
    for cat in ['cl', 'rh', 'scl']:
        balance = getattr(latest, f'{cat}_balance', Decimal('0'))
        if balance > Decimal('0'):
            LeaveTransaction.objects.create(
                user_id=user_id, transaction_type='YEAR_END_LAPSE',
                category=cat.upper(), quantity=balance,
                balance_before=balance, balance_after=Decimal('0'),
                processed_by_user_id=user_id
            )
            results['lapses'].append({
                'category': cat.upper(), 'quantity': balance,
                'reason': 'Year end lapse'
            })
    
    # Process VL - convert to EL
    vl_balance = latest.vl_balance
    if vl_balance > Decimal('0'):
        el_converted = vl_balance / policy.vl_to_el_ratio
        LeaveTransaction.objects.create(
            user_id=user_id, transaction_type='YEAR_END_CONVERSION',
            category='VL', quantity=vl_balance,
            balance_before=vl_balance, balance_after=Decimal('0'),
            processed_by_user_id=user_id
        )
        LeaveTransaction.objects.create(
            user_id=user_id, transaction_type='YEAR_END_CONVERSION',
            category='EL', quantity=el_converted,
            balance_before=latest.el_balance, balance_after=latest.el_balance + el_converted,
            processed_by_user_id=user_id
        )
        results['conversions'].append({
            'from': 'VL', 'to': 'EL', 'quantity': vl_balance,
            'converted_quantity': el_converted
        })
    
    # Process EL, COL - carry forward (no transaction needed, balance persists)
    results['carry_forwards'].append({
        'category': 'EL', 'balance': latest.el_balance,
        'reason': 'Year end carry forward'
    })
    results['carry_forwards'].append({
        'category': 'COL', 'balance': latest.col_balance,
        'reason': 'Year end carry forward'
    })
    
    results['processed'] = True
    return results

def _process_sla_task(task_id: int, threshold_type: Literal['REMINDER', 'ESCALATION']) -> dict:
    """Process SLA threshold event."""
    task = WorkflowTask.objects.get(id=task_id)
    
    if task.status != 'PENDING':
        return {'processed': False, 'reason': 'Task not pending'}
    
    with transaction.atomic():
        if threshold_type == 'REMINDER':
            if task.reminder_threshold_seconds > 0:
                # Check if threshold reached
                elapsed = (timezone.now() - task.created_at).total_seconds()
                if elapsed >= task.reminder_threshold_seconds:
                    if not task.last_reminder_sent_at or \
                       (timezone.now() - task.last_reminder_sent_at).total_seconds() > task.reminder_threshold_seconds:
                        SLAEventLog.objects.create(
                            task=task, event_type='REMINDER',
                            threshold_seconds=task.reminder_threshold_seconds,
                            message=f"Reminder sent for {task.task_type}"
                        )
                        task.last_reminder_sent_at = timezone.now()
                        task.save()
        
        elif threshold_type == 'ESCALATION':
            if task.escalation_threshold_seconds > 0:
                elapsed = (timezone.now() - task.created_at).total_seconds()
                if elapsed >= task.escalation_threshold_seconds:
                    if not task.last_escalation_sent_at or \
                       (timezone.now() - task.last_escalation_sent_at).total_seconds() > task.escalation_threshold_seconds:
                        SLAEventLog.objects.create(
                            task=task, event_type='ESCALATION',
                            threshold_seconds=task.escalation_threshold_seconds,
                            message=f"Escalation sent for {task.task_type}"
                        )
                        task.last_escalation_sent_at = timezone.now()
                        task.save()
    
    return {'processed': True, 'event_type': threshold_type}
