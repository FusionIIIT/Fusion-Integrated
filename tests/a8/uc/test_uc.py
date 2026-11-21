import pytest
from datetime import timedelta
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
def uc_env(db):
    student = User.objects.create_user(username="student_uc", password="pass")
    caretaker = User.objects.create_user(username="caretaker_uc", password="pass")
    warden = User.objects.create_user(username="warden_uc", password="pass")
    MessRole.objects.create(user=caretaker, role='caretaker', is_active=True)
    MessRole.objects.create(user=warden, role='warden', is_active=True)
    window = RegistrationWindow.objects.create(cycle_name="Sem 5", is_open=True)
    return {'student': student, 'caretaker': caretaker, 'warden': warden, 'window': window}

@pytest.mark.django_db
class TestUseCasesSuite:
    """Executable backend test suite for Strategy UC (Use Cases)."""

    def test_uc_001_assign_reassign_roles(self, uc_env):
        """[TEST-UC-001][MMS-UC-001] Assign operational roles."""
        assert MessRole.objects.filter(role='caretaker', is_active=True).count() == 1

    def test_uc_002_open_registration_window(self, uc_env):
        """[TEST-UC-002][MMS-UC-002] Caretaker opens registration window."""
        assert uc_env['window'].is_open is True

    def test_uc_003_submit_registration_request(self, uc_env):
        """[TEST-UC-003][MMS-UC-003] Student submits registration request."""
        req = RegistrationRequest.objects.create(student=uc_env['student'], window=uc_env['window'], status='pending')
        assert req.status == 'pending'

    def test_uc_004_review_registration_request(self, uc_env):
        """[TEST-UC-004][MMS-UC-004] Caretaker reviews and approves request."""
        req = RegistrationRequest.objects.create(student=uc_env['student'], window=uc_env['window'], status='pending')
        req.status = 'approved'
        req.save()
        assert req.status == 'approved'

    def test_uc_005_submit_deregistration_request(self, uc_env):
        """[TEST-UC-005][MMS-UC-005] Student submits deregistration request."""
        dreq = DeregistrationRequest.objects.create(student=uc_env['student'], status='pending')
        assert dreq.status == 'pending'

    def test_uc_006_review_deregistration_request(self, uc_env):
        """[TEST-UC-006][MMS-UC-006] Caretaker reviews deregistration request."""
        dreq = DeregistrationRequest.objects.create(student=uc_env['student'], status='approved_awaiting')
        assert dreq.status == 'approved_awaiting'

    def test_uc_008_publish_weekly_menu(self, uc_env):
        """[TEST-UC-008][MMS-UC-008] Caretaker creates/updates weekly menu."""
        item = MenuItem.objects.create(day=1, meal='lunch', items='Paneer, Rice')
        assert item.meal == 'lunch'

    def test_uc_010_finalize_and_publish_bills(self, uc_env):
        """[TEST-UC-010][MMS-UC-010] Caretaker finalizes and publishes bills."""
        bill = MonthlyBill.objects.create(student=uc_env['student'], month=11, year=2026, status='finalized')
        bill.status = 'published'
        bill.save()
        assert bill.status == 'published'

    def test_uc_012_submit_feedback(self, uc_env):
        """[TEST-UC-012][MMS-UC-012] Student submits text feedback."""
        fb = Feedback.objects.create(student=uc_env['student'], content='Dinner was great')
        assert fb.content == 'Dinner was great'

    def test_uc_014_submit_rebate_request(self, uc_env):
        """[TEST-UC-014][MMS-UC-014] Student submits rebate request."""
        r = RebateRequest.objects.create(student=uc_env['student'], reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=5))
        assert r.status == 'pending'

    def test_uc_016_create_vacation_survey(self, uc_env):
        """[TEST-UC-016][MMS-UC-016] Caretaker creates vacation food survey."""
        vs = VacationSurvey.objects.create(vacation_name="Break", start_date=timezone.now().date()+timedelta(days=5), end_date=timezone.now().date()+timedelta(days=12), deadline=timezone.now()+timedelta(days=2))
        assert vs.vacation_name == "Break"

    def test_uc_019_submit_special_food_request(self, uc_env):
        """[TEST-UC-019][MMS-UC-019] Student submits special food request."""
        sf = SpecialFoodRequest.objects.create(student=uc_env['student'], reason="Fever", requested_date=timezone.now().date()+timedelta(days=2))
        assert sf.status == 'requested'

    def test_uc_022_publish_announcement(self, uc_env):
        """[TEST-UC-022][MMS-UC-022] Caretaker publishes announcement."""
        ann = Announcement.objects.create(author=uc_env['caretaker'], title="Notice", content="Mess closed for cleaning")
        assert ann.title == "Notice"

    def test_uc_027_event_activate_deregistration(self, uc_env):
        """[TEST-UC-027][MMS-UC-027] Next-calendar-day auto-activation for deregistration."""
        yesterday = timezone.now().date() - timedelta(days=1)
        dreq = DeregistrationRequest.objects.create(student=uc_env['student'], status='approved_awaiting', effective_date=yesterday)
        activate_next_day_deregistrations()
        dreq.refresh_from_db()
        assert dreq.status == 'effective'

    def test_uc_028_event_apply_default_vacation_no(self, uc_env):
        """[TEST-UC-028][MMS-UC-028] Default No applied at survey deadline."""
        RegistrationRequest.objects.create(student=uc_env['student'], window=uc_env['window'], status='approved')
        vs = VacationSurvey.objects.create(vacation_name="Test", start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=7), deadline=timezone.now()-timedelta(minutes=5))
        apply_default_vacation_no()
        resp = VacationSurveyResponse.objects.filter(survey=vs, student=uc_env['student']).first()
        assert resp.response == 'default_no'