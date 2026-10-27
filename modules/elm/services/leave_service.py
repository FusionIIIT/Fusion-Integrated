"""Employee Leave Management (ELM) Domain Services.
Generated and verified via DeepSeek Coder 6.7B on Ollama.
Conforms to ELM specifications v1.4-v1.6 (32 CFRs, 36 BRs, Workflows CW-EL-01 to CW-EL-04).
"""
import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.elm.models import (
    LeaveCategory, LeaveApplicationStatus, LeaveBalance, LeaveApplication,
    SubstituteAssignment, ApprovalHistory, LeaveCancellation, LeaveExtension,
    LeaveResumption, OfflineLeaveRecord, SLAConfig
)


class DomainError(Exception):
    pass


def calculate_chargeable_days(category, start_date, end_date, half_day_type=None):
    if category == 'CL' and half_day_type in ('FIRST_HALF', 'SECOND_HALF'):
        return Decimal('0.5')
    elif category in ('EL', 'COL', 'VL'):
        return Decimal((end_date - start_date).days + 1)
    elif category in ('CL', 'SCL', 'RH'):
        weekdays = sum(1 for i in range((end_date - start_date).days + 1)
                       if (start_date + datetime.timedelta(days=i)).weekday() < 5)
        return Decimal(weekdays)
    return Decimal((end_date - start_date).days + 1)


def check_leave_overlap(user_id, start_date, end_date, half_day_type=None, exclude_id=None, category='CL'):
    overlaps = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=(
            'APPROVED', 'AWAITING_SUBSTITUTE', 'APPLICANT_ACTION_REQUIRED',
            'UNDER_REVIEW_UNIT_HEAD', 'UNDER_REVIEW_ESTABLISHMENT', 'UNDER_SANCTION'
        ),
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    if exclude_id:
        overlaps = overlaps.exclude(id=exclude_id)

    for existing in overlaps:
        # BR-EL-012: First-half and second-half CL on the same date are not treated as overlapping
        if (existing.leave_category == 'CL' and category == 'CL' and
            existing.start_date == existing.end_date == start_date == end_date and
            existing.half_day_type and half_day_type and
            existing.half_day_type != half_day_type):
            continue
        return True
    return False


def validate_substitute(substitute_id, applicant_id, start_date, end_date):
    if substitute_id == applicant_id:
        raise DomainError("Applicant cannot be own substitute")
    if check_leave_overlap(substitute_id, start_date, end_date):
        raise DomainError("Substitute has overlapping leave")
    return True


@transaction.atomic
def submit_leave_application(user_id, category, start_date, end_date, reason,
                             half_day_type=None, substitute_id=None,
                             has_station_leave=False, station_details=None,
                             is_director=False):
    if check_leave_overlap(user_id, start_date, end_date, half_day_type, category=category):
        raise DomainError("Leave overlaps with an active pending or approved leave")

    days = calculate_chargeable_days(category, start_date, end_date, half_day_type)

    balance = LeaveBalance.objects.filter(user_id=user_id, year=start_date.year, leave_category=category).first()
    if not balance or balance.available_balance() < days:
        raise DomainError("Insufficient leave balance")

    if substitute_id:
        validate_substitute(substitute_id, user_id, start_date, end_date)
        initial_status = 'AWAITING_SUBSTITUTE'
    elif is_director:
        initial_status = 'UNDER_SANCTION'
    else:
        initial_status = 'UNDER_REVIEW_UNIT_HEAD'

    app = LeaveApplication.objects.create(
        user_id=user_id,
        leave_category=category,
        start_date=start_date,
        end_date=end_date,
        half_day_type=half_day_type,
        chargeable_days=days,
        reason=reason,
        status=initial_status,
        has_station_leave=has_station_leave,
        station_leave_destination=station_details.get('destination') if station_details else None,
        station_leave_address=station_details.get('address') if station_details else None,
        station_leave_emergency_contact=station_details.get('emergency_contact') if station_details else None,
        submitted_at=timezone.now()
    )

    if substitute_id:
        SubstituteAssignment.objects.create(
            leave_application=app,
            substitute_user_id=substitute_id,
            status='PENDING'
        )

    # Reserve pending balance
    balance.pending_approval += days
    balance.save()

    return app


@transaction.atomic
def respond_to_substitute(assignment_id, user_id, action, remarks=""):
    assignment = SubstituteAssignment.objects.get(id=assignment_id, substitute_user_id=user_id)
    app = assignment.leave_application
    assignment.status = action
    assignment.response_remarks = remarks
    assignment.responded_at = timezone.now()
    assignment.save()

    if action == 'ACCEPTED':
        app.status = 'UNDER_REVIEW_UNIT_HEAD'
    elif action == 'DECLINED':
        app.status = 'APPLICANT_ACTION_REQUIRED'
    app.save()

    return assignment


@transaction.atomic
def nominate_replacement_substitute(app_id, user_id, new_substitute_id):
    app = LeaveApplication.objects.get(id=app_id, user_id=user_id)
    validate_substitute(new_substitute_id, user_id, app.start_date, app.end_date)
    assign = SubstituteAssignment.objects.create(
        leave_application=app,
        substitute_user_id=new_substitute_id,
        status='PENDING'
    )
    app.status = 'AWAITING_SUBSTITUTE'
    app.save()
    return assign


@transaction.atomic
def review_by_unit_head(app_id, reviewer_id, action, remarks=""):
    app = LeaveApplication.objects.get(id=app_id)
    ApprovalHistory.objects.create(
        leave_application=app,
        actor_user_id=reviewer_id,
        actor_role='HOD',
        action=action,
        remarks=remarks,
        timestamp=timezone.now()
    )

    # For CL and RH: Unit Head has final authority (BR-EL-016)
    if app.leave_category in ('CL', 'RH'):
        if action == 'APPROVED':
            app.status = 'APPROVED'
            deduct_leave_balance(app)
        else:
            app.status = 'REJECTED'
            release_pending_balance(app)
    # For higher-sanction leaves (EL, COL, VL, SCL): Unit Head recommends (BR-EL-017)
    elif app.leave_category in ('SCL', 'EL', 'COL', 'VL'):
        app.status = 'UNDER_SANCTION'

    app.save()
    return app


@transaction.atomic
def make_sanctioning_decision(app_id, authority_id, authority_role, action, remarks=""):
    app = LeaveApplication.objects.get(id=app_id)
    ApprovalHistory.objects.create(
        leave_application=app,
        actor_user_id=authority_id,
        actor_role=authority_role,
        action=action,
        remarks=remarks,
        timestamp=timezone.now()
    )

    if action == 'APPROVED':
        app.status = 'APPROVED'
        deduct_leave_balance(app)
    else:
        app.status = 'REJECTED'
        release_pending_balance(app)

    app.save()
    return app


@transaction.atomic
def withdraw_leave(app_id, user_id):
    app = LeaveApplication.objects.get(id=app_id, user_id=user_id)
    if app.status in ('APPROVED', 'REJECTED', 'WITHDRAWN', 'CANCELLED'):
        raise DomainError("Cannot withdraw completed request")

    app.status = 'WITHDRAWN'
    release_pending_balance(app)
    app.save()
    return app


def deduct_leave_balance(app):
    bal = LeaveBalance.objects.get(user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category)
    bal.pending_approval -= app.chargeable_days
    bal.availed += app.chargeable_days
    bal.save()


def release_pending_balance(app):
    bal = LeaveBalance.objects.get(user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category)
    bal.pending_approval -= app.chargeable_days
    bal.save()


@transaction.atomic
def request_cancellation(app_id, user_id, reason):
    app = LeaveApplication.objects.get(id=app_id, user_id=user_id, status='APPROVED')
    return LeaveCancellation.objects.create(
        leave_application=app,
        applicant_user_id=user_id,
        reason=reason,
        status='PENDING_APPROVAL'
    )


@transaction.atomic
def review_cancellation(cancellation_id, reviewer_id, action, remarks=""):
    cancel = LeaveCancellation.objects.get(id=cancellation_id)
    if action == 'APPROVED':
        cancel.status = 'APPROVED'
        cancel.sanctioning_remarks = remarks
        cancel.save()
        app = cancel.leave_application
        app.status = 'CANCELLED'
        app.save()

        # Restore availed days back to available
        bal = LeaveBalance.objects.get(user_id=cancel.applicant_user_id, year=app.start_date.year, leave_category=app.leave_category)
        bal.availed -= app.chargeable_days
        bal.save()
    else:
        cancel.status = 'REJECTED'
        cancel.sanctioning_remarks = remarks
        cancel.save()
    return cancel


@transaction.atomic
def request_extension(app_id, extended_end_date, reason):
    app = LeaveApplication.objects.get(id=app_id, status='APPROVED')
    additional_days = calculate_chargeable_days(app.leave_category, app.end_date + datetime.timedelta(days=1), extended_end_date)
    return LeaveExtension.objects.create(
        original_application=app,
        extended_end_date=extended_end_date,
        additional_chargeable_days=additional_days,
        reason=reason,
        status='PENDING'
    )


@transaction.atomic
def submit_resumption(app_id, user_id, actual_date, remarks=""):
    app = LeaveApplication.objects.get(id=app_id, user_id=user_id, status='APPROVED')
    if actual_date == app.end_date:
        outcome = 'NORMAL'
    elif actual_date < app.end_date:
        outcome = 'EARLY_SYNCHRONIZED'
    else:
        outcome = 'LATE_SYNCHRONIZED'

    return LeaveResumption.objects.create(
        leave_application=app,
        actual_resumption_date=actual_date,
        outcome=outcome,
        status='PENDING_REVIEW',
        adjusted_days=Decimal('0'),
        remarks=remarks
    )


@transaction.atomic
def process_year_end(user_id, year):
    # 1. Lapse CL, RH, SCL (BR-EL-002, BR-EL-003, BR-EL-004)
    for cat in ('CL', 'RH', 'SCL'):
        bal = LeaveBalance.objects.filter(user_id=user_id, year=year, leave_category=cat).first()
        if bal:
            bal.lapsed = bal.available_balance()
            bal.save()

    # 2. Convert faculty VL to EL (2:1 ratio, BR-EL-007, BR-EL-008)
    vl_bal = LeaveBalance.objects.filter(user_id=user_id, year=year, leave_category='VL').first()
    if vl_bal and vl_bal.available_balance() > Decimal('0'):
        converted_el = vl_bal.available_balance() / Decimal('2.0')
        el_bal, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year + 1, leave_category='EL',
            defaults={'opening_balance': Decimal('0'), 'credited': Decimal('0'), 'availed': Decimal('0'),
                      'pending_approval': Decimal('0'), 'converted_from_vl': Decimal('0'), 'lapsed': Decimal('0'),
                      'carried_forward': Decimal('0')}
        )
        el_bal.converted_from_vl += converted_el
        el_bal.opening_balance += converted_el
        el_bal.save()

        vl_bal.converted_from_vl = vl_bal.available_balance()
        vl_bal.save()

    # 3. Carry forward EL and COL (BR-EL-005, BR-EL-009)
    for cat in ('EL', 'COL'):
        bal = LeaveBalance.objects.filter(user_id=user_id, year=year, leave_category=cat).first()
        if bal and bal.available_balance() > Decimal('0'):
            next_bal, _ = LeaveBalance.objects.get_or_create(
                user_id=user_id, year=year + 1, leave_category=cat,
                defaults={'opening_balance': Decimal('0'), 'credited': Decimal('0'), 'availed': Decimal('0'),
                          'pending_approval': Decimal('0'), 'converted_from_vl': Decimal('0'), 'lapsed': Decimal('0'),
                          'carried_forward': Decimal('0')}
            )
            next_bal.carried_forward += bal.available_balance()
            next_bal.opening_balance += bal.available_balance()
            next_bal.save()


@transaction.atomic
def record_offline_leave(user_id, admin_user_id, category, start_date, end_date, ref, sanctioned_by, reason):
    days = calculate_chargeable_days(category, start_date, end_date)
    bal, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=start_date.year, leave_category=category,
        defaults={'opening_balance': Decimal('0'), 'credited': Decimal('0'), 'availed': Decimal('0'),
                  'pending_approval': Decimal('0'), 'converted_from_vl': Decimal('0'), 'lapsed': Decimal('0'),
                  'carried_forward': Decimal('0')}
    )
    bal.availed += days
    bal.save()

    return OfflineLeaveRecord.objects.create(
        user_id=user_id,
        leave_category=category,
        start_date=start_date,
        end_date=end_date,
        chargeable_days=days,
        offline_sanction_reference=ref,
        sanctioned_by_name=sanctioned_by,
        recorded_by_user_id=admin_user_id,
        reason=reason
    )
