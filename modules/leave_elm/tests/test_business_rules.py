from decimal import Decimal
from datetime import date, timedelta
import pytest
from django.core.exceptions import ValidationError

from modules.leave_elm.models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    LeaveAction,
    HolidayCalendar,
)
from modules.leave_elm.services import (
    calculate_leave_days,
    check_leave_overlap,
    apply_leave,
    respond_substitute,
    nominate_new_substitute,
    process_unit_head_decision,
    process_higher_sanction_decision,
    withdraw_application,
    cancel_approved_leave,
    convert_faculty_vl_to_el,
    process_resumption,
)


@pytest.fixture(autouse=True)
def setup_leave_types_and_calendar(db):
    """Seed the 6 canonical leave types and sample calendar."""
    LeaveType.objects.all().delete()
    HolidayCalendar.objects.all().delete()

    cl = LeaveType.objects.create(code='CL', name='Casual Leave', max_days_per_year=Decimal('8.0'), is_carry_forward=False)
    rh = LeaveType.objects.create(code='RH', name='Restricted Holiday', max_days_per_year=Decimal('2.0'), is_carry_forward=False)
    scl = LeaveType.objects.create(code='SCL', name='Special Casual Leave', max_days_per_year=Decimal('15.0'), is_carry_forward=False)
    el = LeaveType.objects.create(code='EL', name='Earned Leave', max_days_per_year=Decimal('30.0'), is_carry_forward=True)
    col = LeaveType.objects.create(code='COL', name='Commuted Leave', max_days_per_year=Decimal('20.0'), is_carry_forward=True, requires_medical_evidence=True)
    vl = LeaveType.objects.create(code='VL', name='Vacation Leave', max_days_per_year=Decimal('60.0'), is_carry_forward=False, requires_vacation_period=True)

    # Sample published calendar
    # 2026-10-15: Restricted Holiday (RH)
    HolidayCalendar.objects.create(date=date(2026, 10, 15), name='Govardhan Puja', is_restricted_holiday=True, year=2026)
    # 2026-10-02: Closed Holiday (Gandhi Jayanti) - Friday
    HolidayCalendar.objects.create(date=date(2026, 10, 2), name='Gandhi Jayanti', is_restricted_holiday=False, year=2026)

    return {'CL': cl, 'RH': rh, 'SCL': scl, 'EL': el, 'COL': col, 'VL': vl}


@pytest.mark.django_db
class TestBusinessRulesCalculations:
    def test_br_el_010_half_day_cl_treatment(self):
        """BR-EL-010: Half-day CL consumes exactly 0.5 days."""
        days = calculate_leave_days(
            leave_type_code='CL',
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 5),
            half_day=True,
            half_day_period='FIRST_HALF'
        )
        assert days == Decimal('0.5')

    def test_br_el_011_continuous_day_counting_el_col_vl(self):
        """BR-EL-011: For EL, COL, VL, intervening weekends count as leave days."""
        # Friday to Monday = 4 continuous calendar days
        friday = date(2026, 10, 2)
        monday = date(2026, 10, 5)
        days_el = calculate_leave_days('EL', friday, monday)
        assert days_el == Decimal('4.0')

        days_col = calculate_leave_days('COL', friday, monday)
        assert days_col == Decimal('4.0')

        days_vl = calculate_leave_days('VL', friday, monday)
        assert days_vl == Decimal('4.0')

    def test_br_el_011_working_day_counting_cl_scl_rh(self):
        """BR-EL-011: For CL, SCL, RH, intervening weekends and closed holidays do not count."""
        # 2026-10-01 (Thu) to 2026-10-06 (Tue)
        # Thu (10-01): Working
        # Fri (10-02): Closed Holiday (Gandhi Jayanti) -> excluded!
        # Sat (10-03): Weekend -> excluded!
        # Sun (10-04): Weekend -> excluded!
        # Mon (10-05): Working
        # Tue (10-06): Working
        # Total working days = 3
        start = date(2026, 10, 1)
        end = date(2026, 10, 6)
        days_cl = calculate_leave_days('CL', start, end)
        assert days_cl == Decimal('3.0')


@pytest.mark.django_db
class TestBusinessRulesValidationAndOverlap:
    def test_br_el_012_overlap_prevention(self):
        """BR-EL-012: Prevents overlapping leaves for the same applicant."""
        app1 = apply_leave(
            applicant_username='employee_1',
            leave_type_code='EL',
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 6),
            reason='Conference'
        )
        assert app1.pk is not None

        # Attempting overlapping leave in the same range
        with pytest.raises(ValidationError, match="Impermissible overlap"):
            apply_leave(
                applicant_username='employee_1',
                leave_type_code='CL',
                start_date=date(2026, 11, 4),
                end_date=date(2026, 11, 5),
                reason='Emergency'
            )

    def test_br_el_012_half_day_cl_same_date_exception(self):
        """BR-EL-012: First-half and Second-half CL on the same date do not conflict."""
        dt = date(2026, 11, 10)
        app1 = apply_leave(
            applicant_username='employee_1',
            leave_type_code='CL',
            start_date=dt,
            end_date=dt,
            half_day=True,
            half_day_period='FIRST_HALF',
            reason='Morning duty'
        )
        assert app1.pk is not None

        # Second-half CL on same date must be accepted without overlap error
        app2 = apply_leave(
            applicant_username='employee_1',
            leave_type_code='CL',
            start_date=dt,
            end_date=dt,
            half_day=True,
            half_day_period='SECOND_HALF',
            reason='Afternoon personal'
        )
        assert app2.pk is not None


@pytest.mark.django_db
class TestBusinessRulesSubstituteWorkflow:
    def test_br_el_014_substitute_cannot_be_applicant(self):
        """BR-EL-014: Applicant cannot nominate themselves as substitute."""
        with pytest.raises(ValidationError, match="cannot be their own substitute"):
            apply_leave(
                applicant_username='john',
                leave_type_code='CL',
                start_date=date(2026, 11, 16),
                end_date=date(2026, 11, 17),
                substitute_username='john'
            )

    def test_br_el_014_substitute_cannot_have_overlapping_leave(self):
        """BR-EL-014: Nominated substitute cannot be on leave during the period."""
        # jane has an active approved leave
        jane_app = apply_leave(
            applicant_username='jane',
            leave_type_code='EL',
            start_date=date(2026, 11, 15),
            end_date=date(2026, 11, 20)
        )
        jane_app.status = 'APPROVED'
        jane_app.save()

        with pytest.raises(ValidationError, match="Nominated substitute 'jane' is on leave"):
            apply_leave(
                applicant_username='john',
                leave_type_code='CL',
                start_date=date(2026, 11, 16),
                end_date=date(2026, 11, 17),
                substitute_username='jane'
            )

    def test_br_el_015_substitute_consent_gate_and_recovery(self):
        """BR-EL-015: Substitute consent gates progression to Unit Head."""
        app = apply_leave(
            applicant_username='john',
            leave_type_code='CL',
            start_date=date(2026, 11, 23),
            end_date=date(2026, 11, 24),
            substitute_username='bob'
        )
        assert app.status == 'SUBSTITUTE_PENDING'
        assert app.substitute_status == 'PENDING'

        # If Unit Head attempts decision before substitute acceptance: blocked!
        with pytest.raises(ValidationError, match="not pending Unit Head action"):
            process_unit_head_decision(app, actor_username='unit_head', decision='APPROVE')

        # Bob declines
        respond_substitute(app, substitute_username='bob', accept=False, remarks='Unavailable')
        app.refresh_from_db()
        assert app.status == 'SUBSTITUTE_PENDING'
        assert app.substitute_status == 'DECLINED'

        # John nominates alice
        nominate_new_substitute(app, applicant_username='john', new_substitute_username='alice')
        app.refresh_from_db()
        assert app.substitute_username == 'alice'
        assert app.substitute_status == 'PENDING'

        # Alice accepts
        respond_substitute(app, substitute_username='alice', accept=True, remarks='Accepted')
        app.refresh_from_db()
        assert app.status == 'PENDING_UNIT_HEAD'
        assert app.substitute_status == 'ACCEPTED'


@pytest.mark.django_db
class TestBusinessRulesAuthorityRouting:
    def test_br_el_016_unit_head_final_authority_for_cl_and_rh(self):
        """BR-EL-016: Unit Head gives final approve/reject for CL and RH and deducts balance."""
        app = apply_leave(
            applicant_username='alice',
            leave_type_code='CL',
            start_date=date(2026, 11, 25),
            end_date=date(2026, 11, 26)  # 2 days
        )
        assert app.status == 'PENDING_UNIT_HEAD'

        process_unit_head_decision(app, actor_username='head_cse', decision='APPROVE', remarks='Approved')
        app.refresh_from_db()
        assert app.status == 'APPROVED'

        # Balance was 8.0, now 6.0
        bal = LeaveBalance.objects.get(username='alice', leave_type__code='CL', year=2026)
        assert bal.balance == Decimal('6.0')
        assert bal.utilized == Decimal('2.0')

    def test_br_el_017_and_018_higher_sanction_routing_for_el(self):
        """BR-EL-017 & BR-EL-018: Unit Head recommends SCL/EL/COL/VL, Higher Sanction decides."""
        app = apply_leave(
            applicant_username='bob',
            leave_type_code='EL',
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5)  # 5 days
        )
        assert app.status == 'PENDING_UNIT_HEAD'

        # Unit Head records NOT_RECOMMENDED (BR-EL-017: Still continues to Higher Sanction!)
        process_unit_head_decision(app, actor_username='head_cse', decision='NOT_RECOMMEND', remarks='Heavy workload')
        app.refresh_from_db()
        assert app.status == 'PENDING_HIGHER_SANCTION'
        assert app.unit_head_recommendation == 'NOT_RECOMMENDED'

        # Higher Sanction Authority approves
        process_higher_sanction_decision(app, actor_username='dean_faculty', decision='APPROVE', remarks='Approved on humanitarian grounds')
        app.refresh_from_db()
        assert app.status == 'APPROVED'
        assert app.higher_sanction_authority == 'dean_faculty'

        bal = LeaveBalance.objects.get(username='bob', leave_type__code='EL', year=2026)
        assert bal.balance == Decimal('25.0')  # 30 - 5


@pytest.mark.django_db
class TestBusinessRulesLifecycle:
    def test_br_el_022_immediate_withdrawal_of_pending_request(self):
        """BR-EL-022: Pending request may be immediately withdrawn before final approval."""
        app = apply_leave(
            applicant_username='charlie',
            leave_type_code='CL',
            start_date=date(2026, 12, 8),
            end_date=date(2026, 12, 8)
        )
        withdraw_application(app, applicant_username='charlie', remarks='Plans changed')
        app.refresh_from_db()
        assert app.status == 'WITHDRAWN'

        # Further approval blocked
        with pytest.raises(ValidationError, match="not pending Unit Head action"):
            process_unit_head_decision(app, actor_username='head_cse', decision='APPROVE')

    def test_br_el_023_cancellation_before_start_date_restores_balance(self):
        """BR-EL-023: Cancellation before start date restores deducted balance."""
        start = date(2026, 12, 20)
        end = date(2026, 12, 22)  # 3 days
        app = apply_leave(
            applicant_username='david',
            leave_type_code='EL',
            start_date=start,
            end_date=end
        )
        process_unit_head_decision(app, actor_username='head_cse', decision='RECOMMEND')
        process_higher_sanction_decision(app, actor_username='dean', decision='APPROVE')
        app.refresh_from_db()
        assert app.status == 'APPROVED'

        bal_before = LeaveBalance.objects.get(username='david', leave_type__code='EL', year=2026)
        assert bal_before.balance == Decimal('27.0')

        # Cancel on 2026-12-15 (before start date 2026-12-20)
        cancel_approved_leave(app, applicant_username='david', reason='Meeting rescheduled', current_date=date(2026, 12, 15))
        app.refresh_from_db()
        assert app.status == 'CANCELLED'

        bal_after = LeaveBalance.objects.get(username='david', leave_type__code='EL', year=2026)
        assert bal_after.balance == Decimal('30.0')  # Restored!

    def test_br_el_023_cancellation_on_or_after_start_date_blocked(self):
        """BR-EL-023: Cancellation on or after start date is blocked."""
        start = date(2026, 12, 20)
        end = date(2026, 12, 22)
        app = apply_leave(
            applicant_username='david',
            leave_type_code='EL',
            start_date=start,
            end_date=end
        )
        process_unit_head_decision(app, actor_username='head_cse', decision='RECOMMEND')
        process_higher_sanction_decision(app, actor_username='dean', decision='APPROVE')
        app.refresh_from_db()

        with pytest.raises(ValidationError, match="only be cancelled before its start date"):
            cancel_approved_leave(app, applicant_username='david', reason='Late cancel', current_date=date(2026, 12, 20))


@pytest.mark.django_db
class TestBusinessRulesYearEndConversionAndResumption:
    def test_br_el_007_and_008_vl_to_el_conversion(self):
        """BR-EL-007 & 008: 2 VL : 1 EL year-end conversion including fractions."""
        # Faculty has 45 days VL unused out of 60
        vl_type = LeaveType.objects.get(code='VL')
        el_type = LeaveType.objects.get(code='EL')

        LeaveBalance.objects.create(
            username='prof_smith',
            leave_type=vl_type,
            year=2026,
            balance=Decimal('45.0'),
            credited=Decimal('60.0'),
            utilized=Decimal('15.0')
        )
        LeaveBalance.objects.create(
            username='prof_smith',
            leave_type=el_type,
            year=2026,
            balance=Decimal('10.0'),
            credited=Decimal('10.0'),
            utilized=Decimal('0.0')
        )

        converted_el = convert_faculty_vl_to_el('prof_smith', 2026)
        # 45 / 2 = 22.5 EL
        assert converted_el == Decimal('22.5')

        vl_bal = LeaveBalance.objects.get(username='prof_smith', leave_type=vl_type, year=2026)
        assert vl_bal.balance == Decimal('0.0')  # VL does not carry forward

        el_bal = LeaveBalance.objects.get(username='prof_smith', leave_type=el_type, year=2026)
        assert el_bal.balance == Decimal('32.5')  # 10 + 22.5

    def test_br_el_028_resumption_early_and_late_adjustment(self):
        """BR-EL-028: Resumption earlier or later adjusts balance accordingly."""
        # Approved EL from 2026-10-01 to 2026-10-10 (10 days)
        app = apply_leave(
            applicant_username='staff_1',
            leave_type_code='EL',
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 10)
        )
        process_unit_head_decision(app, actor_username='head', decision='RECOMMEND')
        process_higher_sanction_decision(app, actor_username='dean', decision='APPROVE')
        app.refresh_from_db()
        assert app.days_count == Decimal('10.0')

        # Early resumption on 2026-10-07 (7 days actual instead of 10)
        process_resumption(app, actual_resumption_date=date(2026, 10, 7), actor_username='head', remarks='Early return')
        app.refresh_from_db()
        assert app.days_count == Decimal('7.0')
        assert app.actual_resumption_date == date(2026, 10, 7)

        bal = LeaveBalance.objects.get(username='staff_1', leave_type__code='EL', year=2026)
        # Originally 30 - 10 = 20; with 3 days returned: 23.0
        assert bal.balance == Decimal('23.0')
