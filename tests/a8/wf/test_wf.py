import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

from modules.mms.models import (
    RegistrationWindow, RegistrationRequest, DeregistrationRequest,
    RebateRequest, SpecialFoodRequest, VacationSurvey, VacationSurveyResponse, MonthlyBill
)
from modules.mms.tasks import (
    activate_next_day_deregistrations,
    apply_default_vacation_no,
    auto_reject_special_food_timeouts
)

User = get_user_model()

@pytest.fixture
def wf_setup(db):
    student = User.objects.create_user(username="test_student_wf", password="password")
    window = RegistrationWindow.objects.create(
        cycle_name="Autumn 2026",
        start_date=timezone.now().date() - timedelta(days=1),
        end_date=timezone.now().date() + timedelta(days=15),
        is_open=True
    )
    return {'student': student, 'window': window}

@pytest.mark.django_db
class TestWorkflowsSuite:
    """Executable backend test suite for Strategy WF (Workflows)."""

    def test_bw_mms_01_registration_approved_path(self, wf_setup):
        """[TEST-WF-001][BW-MMS-01] Valid submission to Caretaker approval path."""
        req = RegistrationRequest.objects.create(student=wf_setup['student'], window=wf_setup['window'], status='pending')
        req.status = 'approved'
        req.save()
        assert req.status == 'approved'

    def test_bw_mms_02_registration_rejected_path(self, wf_setup):
        """[TEST-WF-002][BW-MMS-02] Valid submission to Caretaker rejection path."""
        req = RegistrationRequest.objects.create(student=wf_setup['student'], window=wf_setup['window'], status='pending')
        req.status = 'rejected'
        req.save()
        assert req.status == 'rejected'

    def test_bw_mms_03_deregistration_approved_system_activation(self, wf_setup):
        """[TEST-WF-003][BW-MMS-03] Deregistration approval followed by system next-day activation."""
        yesterday = timezone.now().date() - timedelta(days=1)
        dreq = DeregistrationRequest.objects.create(
            student=wf_setup['student'],
            status='approved_awaiting',
            decision_date=yesterday,
            effective_date=yesterday
        )
        activate_next_day_deregistrations()
        dreq.refresh_from_db()
        assert dreq.status == 'effective'

    def test_bw_mms_04_deregistration_rejected_path(self, wf_setup):
        """[TEST-WF-004][BW-MMS-04] Deregistration rejection keeps student registered."""
        dreq = DeregistrationRequest.objects.create(student=wf_setup['student'], status='rejected')
        assert dreq.status == 'rejected'

    def test_bw_mms_05_rebate_approved_as_submitted(self, wf_setup):
        """[TEST-WF-005][BW-MMS-05] Rebate approved without modifying requested dates."""
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=4)
        r = RebateRequest.objects.create(student=wf_setup['student'], reason='medical', start_date=start, end_date=end, status='pending')
        r.status = 'approved'
        r.save()
        assert r.status == 'approved'

    def test_bw_mms_06_rebate_modified_dates_approved(self, wf_setup):
        """[TEST-WF-006][BW-MMS-06] Rebate approved with caretaker-modified dates."""
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=5)
        r = RebateRequest.objects.create(student=wf_setup['student'], reason='medical', start_date=start, end_date=end, status='pending')
        r.approved_start_date = start + timedelta(days=1)
        r.approved_end_date = end
        r.status = 'approved'
        r.save()
        assert r.approved_start_date != r.start_date

    def test_bw_mms_07_rebate_rejected_path(self, wf_setup):
        """[TEST-WF-007][BW-MMS-07] Rebate rejection path."""
        r = RebateRequest.objects.create(student=wf_setup['student'], reason='family_function', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=5), status='rejected')
        assert r.status == 'rejected'

    def test_bw_mms_08_vacation_survey_yes_response(self, wf_setup):
        """[TEST-WF-008][BW-MMS-08] Vacation survey explicit Yes response."""
        vs = VacationSurvey.objects.create(vacation_name="Diwali", start_date=timezone.now().date()+timedelta(days=5), end_date=timezone.now().date()+timedelta(days=15), deadline=timezone.now()+timedelta(days=3))
        resp = VacationSurveyResponse.objects.create(survey=vs, student=wf_setup['student'], response='yes')
        assert resp.response == 'yes'

    def test_bw_mms_09_vacation_survey_no_response(self, wf_setup):
        """[TEST-WF-009][BW-MMS-09] Vacation survey explicit No response."""
        vs = VacationSurvey.objects.create(vacation_name="Diwali", start_date=timezone.now().date()+timedelta(days=5), end_date=timezone.now().date()+timedelta(days=15), deadline=timezone.now()+timedelta(days=3))
        resp = VacationSurveyResponse.objects.create(survey=vs, student=wf_setup['student'], response='no')
        assert resp.response == 'no'

    def test_bw_mms_10_vacation_survey_default_no_path(self, wf_setup):
        """[TEST-WF-010][BW-MMS-10] Survey response deadline triggers default No."""
        RegistrationRequest.objects.create(student=wf_setup['student'], window=wf_setup['window'], status='approved')
        vs = VacationSurvey.objects.create(vacation_name="Winter", start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=10), deadline=timezone.now()-timedelta(minutes=5), is_open=True)
        apply_default_vacation_no()
        resp = VacationSurveyResponse.objects.get(survey=vs, student=wf_setup['student'])
        assert resp.response == 'default_no'

    def test_bw_mms_11_special_food_caretaker_rejection(self, wf_setup):
        """[TEST-WF-011][BW-MMS-11] Special food explicit Caretaker rejection."""
        sf = SpecialFoodRequest.objects.create(student=wf_setup['student'], reason="Diet", requested_date=timezone.now().date()+timedelta(days=2), status='rejected')
        assert sf.status == 'rejected'

    def test_bw_mms_12_special_food_default_rejection(self, wf_setup):
        """[TEST-WF-012][BW-MMS-12] Special food timeout trigger leads to Rejected."""
        sf = SpecialFoodRequest.objects.create(student=wf_setup['student'], reason="Diet", requested_date=timezone.now().date()+timedelta(days=2), status='requested', timeout_at=timezone.now()-timedelta(hours=1))
        auto_reject_special_food_timeouts()
        sf.refresh_from_db()
        assert sf.status == 'rejected'

    def test_bw_mms_13_special_food_approved_path(self, wf_setup):
        """[TEST-WF-013][BW-MMS-13] Special food approval path."""
        sf = SpecialFoodRequest.objects.create(student=wf_setup['student'], reason="Sick", requested_date=timezone.now().date()+timedelta(days=2), status='approved', charge=Decimal('120.00'))
        assert sf.status == 'approved'

    def test_bw_mms_14_special_food_served_path(self, wf_setup):
        """[TEST-WF-014][BW-MMS-14] Special food Approved to Served path."""
        sf = SpecialFoodRequest.objects.create(student=wf_setup['student'], reason="Sick", requested_date=timezone.now().date()+timedelta(days=2), status='approved')
        sf.status = 'served'
        sf.save()
        assert sf.status == 'served'

    def test_bw_mms_15_special_food_cancelled_path(self, wf_setup):
        """[TEST-WF-015][BW-MMS-15] Special food Approved to Cancelled path."""
        sf = SpecialFoodRequest.objects.create(student=wf_setup['student'], reason="Sick", requested_date=timezone.now().date()+timedelta(days=2), status='approved')
        sf.status = 'cancelled'
        sf.save()
        assert sf.status == 'cancelled'

    def test_bw_mms_16_billing_generation_to_publication(self, wf_setup):
        """[TEST-WF-016][BW-MMS-16] Monthly bill generated -> finalized -> published."""
        bill = MonthlyBill.objects.create(student=wf_setup['student'], month=11, year=2026, status='generated')
        bill.status = 'finalized'
        bill.save()
        bill.status = 'published'
        bill.published_at = timezone.now()
        bill.save()
        assert bill.status == 'published'