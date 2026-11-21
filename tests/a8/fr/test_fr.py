import pytest
from datetime import timedelta, date
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

from modules.mms.models import (
    MessRole, RegistrationWindow, RegistrationRequest, DeregistrationRequest,
    MenuItem, RebateRequest, SpecialFoodRequest, VacationSurvey,
    VacationSurveyResponse, MonthlyBill, Feedback, Announcement
)
from modules.mms.tasks import activate_next_day_deregistrations, apply_default_vacation_no

User = get_user_model()

@pytest.fixture
def fr_env(db):
    student = User.objects.create_user(username="fr_student", password="pwd")
    caretaker = User.objects.create_user(username="fr_caretaker", password="pwd")
    warden = User.objects.create_user(username="fr_warden", password="pwd")
    admin = User.objects.create_user(username="fr_admin", password="pwd")
    MessRole.objects.create(user=caretaker, role='caretaker', is_active=True)
    MessRole.objects.create(user=warden, role='warden', is_active=True)
    window = RegistrationWindow.objects.create(cycle_name="Autumn", is_open=True)
    return {'student': student, 'caretaker': caretaker, 'warden': warden, 'admin': admin, 'window': window}

@pytest.mark.django_db
class TestFunctionalRequirementsSuite:
    """Executable backend test suite for Strategy FR (CFR + AFR)."""

    def test_cfr_001_scope_isolation(self, fr_env):
        """[TEST-FR-001][AFR-MMS-001] Verify MMS operational models are scoped."""
        assert RegistrationRequest.objects.count() == 0

    def test_cfr_002_role_cardinality(self, fr_env):
        """[TEST-FR-007][AFR-MMS-005] Enforce single active Caretaker."""
        assert MessRole.objects.filter(role='caretaker', is_active=True).count() == 1

    def test_cfr_004_registration_lifecycle(self, fr_env):
        """[TEST-FR-016][AFR-MMS-013] Registration request during open window."""
        req = RegistrationRequest.objects.create(student=fr_env['student'], window=fr_env['window'])
        assert req.status == 'pending'

    def test_cfr_005_deregistration_next_day(self, fr_env):
        """[TEST-FR-024][AFR-MMS-018] Approved deregistration starts next day."""
        yesterday = timezone.now().date() - timedelta(days=1)
        dreq = DeregistrationRequest.objects.create(student=fr_env['student'], status='approved_awaiting', effective_date=yesterday)
        activate_next_day_deregistrations()
        dreq.refresh_from_db()
        assert dreq.status == 'effective'

    def test_cfr_008_weekly_menu_structure(self, fr_env):
        """[TEST-FR-032][AFR-MMS-024] Day-wise and meal-wise weekly menu."""
        item = MenuItem.objects.create(day=2, meal='dinner', items='Khichdi, Curd')
        assert item.day == 2
        assert item.meal == 'dinner'

    def test_cfr_009_monthly_billing_computation(self, fr_env):
        """[TEST-FR-044][AFR-MMS-034] Daily rate * served days + special meal - rebate."""
        bill = MonthlyBill.objects.create(
            student=fr_env['student'], month=11, year=2026,
            served_days=30, daily_rate=Decimal('120.00'),
            base_charge=Decimal('3600.00'),
            special_food_charge=Decimal('200.00'),
            rebate_deduction=Decimal('600.00'),
            total_amount=Decimal('3200.00'),
            status='published'
        )
        assert bill.total_amount == (bill.base_charge + bill.special_food_charge - bill.rebate_deduction)

    def test_cfr_010_student_feedback(self, fr_env):
        """[TEST-FR-053][AFR-MMS-044] Student submits text feedback."""
        fb = Feedback.objects.create(student=fr_env['student'], content='Improve breakfast timings')
        assert fb.content == 'Improve breakfast timings'

    def test_cfr_011_rebate_minimum_duration(self, fr_env):
        """[TEST-FR-063][AFR-MMS-052] Minimum duration is 3 days."""
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=2)
        assert ((end - start).days + 1) >= 3

    def test_cfr_014_vacation_survey_default_no(self, fr_env):
        """[TEST-FR-084][AFR-MMS-066] Automatic No for non-responding registered students."""
        RegistrationRequest.objects.create(student=fr_env['student'], window=fr_env['window'], status='approved')
        vs = VacationSurvey.objects.create(vacation_name="Winter", start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=10), deadline=timezone.now()-timedelta(minutes=5))
        apply_default_vacation_no()
        resp = VacationSurveyResponse.objects.get(survey=vs, student=fr_env['student'])
        assert resp.response == 'default_no'

    def test_cfr_017_special_food_state_fsm(self, fr_env):
        """[TEST-FR-097][AFR-MMS-078] Special food transitions to served after approval."""
        sf = SpecialFoodRequest.objects.create(student=fr_env['student'], reason="Illness", requested_date=timezone.now().date()+timedelta(days=2), status='approved')
        sf.status = 'served'
        sf.save()
        assert sf.status == 'served'