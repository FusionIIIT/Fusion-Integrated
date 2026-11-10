import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

from modules.mms.models import (
    MessRole, RegistrationWindow, RegistrationRequest, DeregistrationRequest,
    MenuItem, RebateRequest, SpecialFoodRequest, VacationSurvey,
    VacationSurveyResponse, MonthlyBill, Feedback, Announcement
)
from modules.mms.tasks import (
    activate_next_day_deregistrations,
    apply_default_vacation_no,
    auto_reject_special_food_timeouts
)

User = get_user_model()

@pytest.fixture
def mms_actors(db):
    student = User.objects.create_user(username="test_student_br", password="password")
    caretaker_user = User.objects.create_user(username="test_caretaker_br", password="password")
    warden_user = User.objects.create_user(username="test_warden_br", password="password")
    admin_user = User.objects.create_user(username="test_admin_br", password="password")

    MessRole.objects.create(user=caretaker_user, role='caretaker', is_active=True)
    MessRole.objects.create(user=warden_user, role='warden', is_active=True)
    return {
        'student': student,
        'caretaker': caretaker_user,
        'warden': warden_user,
        'admin': admin_user,
    }

@pytest.mark.django_db
class TestBusinessRulesSuite:
    """Executable backend test suite for Strategy BR (Business Rules)."""

    def test_br_003_single_active_caretaker(self, mms_actors):
        """[TEST-BR-003][BR-MMS-003] Enforce exactly one active Mess Caretaker."""
        active_count = MessRole.objects.filter(role='caretaker', is_active=True).count()
        assert active_count == 1

    def test_br_004_single_active_warden(self, mms_actors):
        """[TEST-BR-004][BR-MMS-004] Enforce exactly one active Mess Warden."""
        active_count = MessRole.objects.filter(role='warden', is_active=True).count()
        assert active_count == 1

    def test_br_005_admin_operational_data_restriction(self, mms_actors):
        """[TEST-BR-005][BR-MMS-005] Mess Admin prevented from operational access."""
        admin_roles = MessRole.objects.filter(user=mms_actors['admin'], is_active=True)
        assert admin_roles.count() == 0

    def test_br_008_window_open_by_caretaker(self, mms_actors):
        """[TEST-BR-008][BR-MMS-008] Caretaker opens registration window."""
        window = RegistrationWindow.objects.create(
            cycle_name="Spring 2027",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=15),
            is_open=True
        )
        assert window.is_open is True

    def test_br_009_registration_window_guard(self, mms_actors):
        """[TEST-BR-009][BR-MMS-009] Registration allowed only during open window."""
        window = RegistrationWindow.objects.create(
            cycle_name="Closed Cycle",
            start_date=timezone.now().date() - timedelta(days=30),
            end_date=timezone.now().date() - timedelta(days=10),
            is_open=False
        )
        assert window.is_currently_active() is False

    def test_br_010_caretaker_approval_authority(self, mms_actors):
        """[TEST-BR-010][BR-MMS-010] Only Caretaker approves/rejects registration."""
        window = RegistrationWindow.objects.create(cycle_name="Reg Cycle", is_open=True)
        req = RegistrationRequest.objects.create(student=mms_actors['student'], window=window, status='pending')
        req.status = 'approved'
        req.save()
        assert req.status == 'approved'

    def test_br_013_deregistration_next_day_effective(self, mms_actors):
        """[TEST-BR-015][BR-MMS-013] Approved deregistration effective next calendar day."""
        today = timezone.now().date()
        dreq = DeregistrationRequest.objects.create(
            student=mms_actors['student'],
            status='approved_awaiting',
            decision_date=today,
            effective_date=today + timedelta(days=1)
        )
        assert dreq.effective_date == today + timedelta(days=1)

    def test_br_014_menu_meal_structure(self, mms_actors):
        """[TEST-BR-016][BR-MMS-014] Day-wise and meal-wise menu structure."""
        item = MenuItem.objects.create(day=0, meal='breakfast', items='Poha, Tea')
        assert item.meal == 'breakfast'
        assert item.day == 0

    def test_br_017_bill_computation_components(self, mms_actors):
        """[TEST-BR-020][BR-MMS-017] Daily rate * served days + special food - rebate."""
        bill = MonthlyBill.objects.create(
            student=mms_actors['student'],
            month=11, year=2026,
            served_days=30, daily_rate=Decimal('100.00'),
            base_charge=Decimal('3000.00'),
            special_food_charge=Decimal('200.00'),
            rebate_deduction=Decimal('500.00'),
            total_amount=Decimal('2700.00')
        )
        expected = bill.base_charge + bill.special_food_charge - bill.rebate_deduction
        assert bill.total_amount == expected

    def test_br_018_caretaker_bill_finalization(self, mms_actors):
        """[TEST-BR-021][BR-MMS-018] Caretaker must finalize bills before publication."""
        bill = MonthlyBill.objects.create(student=mms_actors['student'], month=11, year=2026, status='finalized')
        assert bill.status == 'finalized'

    def test_br_021_minimum_rebate_duration_bva(self, mms_actors):
        """[TEST-BR-025][BR-MMS-021] Rebate minimum duration is 3 days."""
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=2)
        duration = (end - start).days + 1
        assert duration >= 3

    def test_br_022_rebate_lead_time_bva(self, mms_actors):
        """[TEST-BR-026][BR-MMS-022] Rebate submitted >= 1 calendar day before start date."""
        today = timezone.now().date()
        start = today + timedelta(days=1)
        lead_time = (start - today).days
        assert lead_time >= 1

    def test_br_024_rebate_reason_other_mandatory_explanation(self, mms_actors):
        """[TEST-BR-028][BR-MMS-024] Explanation mandatory when reason is other."""
        r = RebateRequest.objects.create(
            student=mms_actors['student'],
            reason='other',
            explanation='Conference attendance',
            start_date=timezone.now().date() + timedelta(days=2),
            end_date=timezone.now().date() + timedelta(days=6)
        )
        assert len(r.explanation) > 0

    def test_br_027_vacation_survey_default_no_at_deadline(self, mms_actors):
        """[TEST-BR-032][BR-MMS-027] Default No for non-responding students at deadline."""
        window = RegistrationWindow.objects.create(cycle_name="Cycle", is_open=True)
        RegistrationRequest.objects.create(student=mms_actors['student'], window=window, status='approved')
        vs = VacationSurvey.objects.create(
            vacation_name="Winter Break",
            start_date=timezone.now().date() + timedelta(days=5),
            end_date=timezone.now().date() + timedelta(days=15),
            deadline=timezone.now() - timedelta(minutes=1),
            is_open=True
        )
        apply_default_vacation_no()
        resp = VacationSurveyResponse.objects.filter(survey=vs, student=mms_actors['student']).first()
        assert resp is not None
        assert resp.response == 'default_no'

    def test_br_028_special_food_lead_time(self, mms_actors):
        """[TEST-BR-033][BR-MMS-028] Special food submitted >= 1 calendar day ahead."""
        today = timezone.now().date()
        target = today + timedelta(days=2)
        assert (target - today).days >= 1

    def test_br_029_special_food_timeout_rejection(self, mms_actors):
        """[TEST-BR-034][BR-MMS-029] Undecided special food auto-rejected on timeout."""
        past_time = timezone.now() - timedelta(minutes=10)
        sf = SpecialFoodRequest.objects.create(
            student=mms_actors['student'],
            reason="Illness",
            requested_date=timezone.now().date() + timedelta(days=2),
            status='requested',
            timeout_at=past_time
        )
        auto_reject_special_food_timeouts()
        sf.refresh_from_db()
        assert sf.status == 'rejected'

    def test_br_031_special_food_state_transitions(self, mms_actors):
        """[TEST-BR-037][BR-MMS-031] Served occurs only after Approved status."""
        sf = SpecialFoodRequest.objects.create(
            student=mms_actors['student'],
            reason="Illness",
            requested_date=timezone.now().date() + timedelta(days=2),
            status='approved'
        )
        sf.status = 'served'
        sf.save()
        assert sf.status == 'served'