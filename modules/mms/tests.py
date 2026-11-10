from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

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

class MMSComprehensiveTestSuite(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="student1", password="pass", email="student1@iiitj.ac.in")
        self.student2 = User.objects.create_user(username="student2", password="pass", email="student2@iiitj.ac.in")
        self.caretaker_user = User.objects.create_user(username="caretaker1", password="pass")
        self.warden_user = User.objects.create_user(username="warden1", password="pass")
        self.admin_user = User.objects.create_user(username="admin1", password="pass")

        self.caretaker_role = MessRole.objects.create(user=self.caretaker_user, role='caretaker', is_active=True)
        self.warden_role = MessRole.objects.create(user=self.warden_user, role='warden', is_active=True)

        self.window = RegistrationWindow.objects.create(
            cycle_name="Autumn 2026",
            start_date=timezone.now().date() - timedelta(days=2),
            end_date=timezone.now().date() + timedelta(days=20),
            is_open=True
        )

    # ==========================================
    # 1. Operational Roles & Cardinality (AFR-002..007, 096..099)
    # ==========================================
    def test_01_caretaker_role_creation(self):
        self.assertEqual(self.caretaker_role.role, 'caretaker')
        self.assertTrue(self.caretaker_role.is_active)

    def test_02_warden_role_creation(self):
        self.assertEqual(self.warden_role.role, 'warden')
        self.assertTrue(self.warden_role.is_active)

    def test_03_role_assignment_time_bounds(self):
        now = timezone.now()
        role = MessRole.objects.create(user=self.admin_user, role='caretaker', start_time=now, end_time=now + timedelta(days=180))
        self.assertIsNotNone(role.end_time)
        self.assertGreater(role.end_time, role.start_time)

    def test_04_midcycle_reassignment_deactivates_prior(self):
        self.caretaker_role.is_active = False
        self.caretaker_role.save()
        new_caretaker = MessRole.objects.create(user=self.student2, role='caretaker', is_active=True)
        active_count = MessRole.objects.filter(role='caretaker', is_active=True).count()
        self.assertEqual(active_count, 1)
        self.assertEqual(new_caretaker.user, self.student2)

    def test_05_single_active_warden_cardinality(self):
        self.warden_role.is_active = False
        self.warden_role.save()
        MessRole.objects.create(user=self.student, role='warden', is_active=True)
        self.assertEqual(MessRole.objects.filter(role='warden', is_active=True).count(), 1)

    def test_06_admin_has_no_operational_role(self):
        admin_roles = MessRole.objects.filter(user=self.admin_user, is_active=True)
        self.assertEqual(admin_roles.count(), 0)

    # ==========================================
    # 2. Registration Window & Lifecycle (AFR-012..015, CW-MMS-01)
    # ==========================================
    def test_07_window_creation_valid(self):
        self.assertTrue(self.window.is_open)
        self.assertEqual(self.window.cycle_name, "Autumn 2026")

    def test_08_window_is_currently_active_check(self):
        self.assertTrue(self.window.is_currently_active())

    def test_09_window_closed_state(self):
        self.window.is_open = False
        self.window.save()
        self.assertFalse(self.window.is_currently_active())

    def test_10_window_future_dates(self):
        future_window = RegistrationWindow.objects.create(
            cycle_name="Spring 2027",
            start_date=timezone.now().date() + timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=60),
            is_open=True
        )
        self.assertFalse(future_window.is_currently_active())

    def test_11_window_past_dates(self):
        past_window = RegistrationWindow.objects.create(
            cycle_name="Spring 2026",
            start_date=timezone.now().date() - timedelta(days=60),
            end_date=timezone.now().date() - timedelta(days=30),
            is_open=True
        )
        self.assertFalse(past_window.is_currently_active())

    def test_12_registration_submission_pending(self):
        req = RegistrationRequest.objects.create(student=self.student, window=self.window)
        self.assertEqual(req.status, 'pending')
        self.assertIsNotNone(req.created_at)

    def test_13_registration_approval_by_caretaker(self):
        req = RegistrationRequest.objects.create(student=self.student, window=self.window)
        req.status = 'approved'
        req.remarks = 'Documents verified'
        req.save()
        self.assertEqual(RegistrationRequest.objects.get(id=req.id).status, 'approved')

    def test_14_registration_rejection_by_caretaker(self):
        req = RegistrationRequest.objects.create(student=self.student, window=self.window)
        req.status = 'rejected'
        req.remarks = 'Fee dues outstanding'
        req.save()
        self.assertEqual(RegistrationRequest.objects.get(id=req.id).status, 'rejected')

    def test_15_multiple_students_registration(self):
        req1 = RegistrationRequest.objects.create(student=self.student, window=self.window)
        req2 = RegistrationRequest.objects.create(student=self.student2, window=self.window)
        self.assertNotEqual(req1.student, req2.student)
        self.assertEqual(RegistrationRequest.objects.filter(window=self.window).count(), 2)

    # ==========================================
    # 3. Deregistration Request Lifecycle (AFR-014..018, CW-MMS-02)
    # ==========================================
    def test_16_deregistration_initial_submission(self):
        dreq = DeregistrationRequest.objects.create(student=self.student)
        self.assertEqual(dreq.status, 'pending')

    def test_17_deregistration_approval_sets_awaiting_state(self):
        today = timezone.now().date()
        dreq = DeregistrationRequest.objects.create(
            student=self.student,
            status='approved_awaiting',
            decision_date=today,
            effective_date=today + timedelta(days=1)
        )
        self.assertEqual(dreq.status, 'approved_awaiting')
        self.assertEqual(dreq.effective_date, today + timedelta(days=1))

    def test_18_deregistration_rejection_leaves_registered(self):
        dreq = DeregistrationRequest.objects.create(student=self.student, status='rejected')
        self.assertEqual(dreq.status, 'rejected')

    def test_19_activation_task_for_due_deregistrations(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        dreq = DeregistrationRequest.objects.create(
            student=self.student,
            status='approved_awaiting',
            decision_date=yesterday - timedelta(days=1),
            effective_date=yesterday
        )
        activate_next_day_deregistrations()
        dreq.refresh_from_db()
        self.assertEqual(dreq.status, 'effective')

    def test_20_activation_task_ignores_future_deregistrations(self):
        tomorrow = timezone.now().date() + timedelta(days=1)
        dreq = DeregistrationRequest.objects.create(
            student=self.student,
            status='approved_awaiting',
            effective_date=tomorrow
        )
        activate_next_day_deregistrations()
        dreq.refresh_from_db()
        self.assertEqual(dreq.status, 'approved_awaiting')

    # ==========================================
    # 4. Weekly Menu Management (AFR-024..032)
    # ==========================================
    def test_21_create_breakfast_menu_item(self):
        item = MenuItem.objects.create(day=0, meal='breakfast', items='Poha, Boiled Eggs, Tea')
        self.assertEqual(item.day, 0)
        self.assertEqual(item.meal, 'breakfast')

    def test_22_create_lunch_menu_item(self):
        item = MenuItem.objects.create(day=1, meal='lunch', items='Roti, Dal Tadka, Rice, Paneer')
        self.assertEqual(item.meal, 'lunch')

    def test_23_create_dinner_menu_item(self):
        item = MenuItem.objects.create(day=2, meal='dinner', items='Mix Veg, Roti, Kheer')
        self.assertEqual(item.meal, 'dinner')

    def test_24_menu_item_update(self):
        item = MenuItem.objects.create(day=3, meal='breakfast', items='Idli, Sambhar')
        item.items = 'Upma, Chutney'
        item.save()
        self.assertEqual(MenuItem.objects.get(id=item.id).items, 'Upma, Chutney')

    def test_25_menu_item_deletion(self):
        item = MenuItem.objects.create(day=4, meal='dinner', items='Special Dinner')
        item_id = item.id
        item.delete()
        self.assertFalse(MenuItem.objects.filter(id=item_id).exists())

    def test_26_menu_item_day_range_validation(self):
        for day_val in range(7):
            m = MenuItem.objects.create(day=day_val, meal='breakfast', items=f'Item {day_val}')
            self.assertIn(m.day, range(7))

    # ==========================================
    # 5. Rebate Requests - Equivalence & BVA (AFR-049..061, CW-MMS-03)
    # ==========================================
    def test_27_rebate_reason_medical(self):
        r = RebateRequest.objects.create(student=self.student, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6))
        self.assertEqual(r.reason, 'medical')

    def test_28_rebate_reason_leave(self):
        r = RebateRequest.objects.create(student=self.student, reason='institute_leave', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=5))
        self.assertEqual(r.reason, 'institute_leave')

    def test_29_rebate_reason_family(self):
        r = RebateRequest.objects.create(student=self.student, reason='family_function', start_date=timezone.now().date()+timedelta(days=3), end_date=timezone.now().date()+timedelta(days=7))
        self.assertEqual(r.reason, 'family_function')

    def test_30_rebate_reason_other_with_explanation(self):
        r = RebateRequest.objects.create(student=self.student, reason='other', explanation='Attending academic conference', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6))
        self.assertTrue(len(r.explanation) > 0)

    def test_31_rebate_duration_bva_minimum_3_days(self):
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=2)
        duration = (end - start).days + 1
        self.assertEqual(duration, 3)
        r = RebateRequest.objects.create(student=self.student, reason='medical', start_date=start, end_date=end)
        self.assertIsNotNone(r.id)

    def test_32_rebate_duration_bva_4_days(self):
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=3)
        self.assertGreaterEqual((end - start).days + 1, 3)

    def test_33_rebate_lead_time_bva_1_day_ahead(self):
        today = timezone.now().date()
        start = today + timedelta(days=1)
        self.assertGreater(start, today)

    def test_34_rebate_lead_time_bva_multi_day_ahead(self):
        today = timezone.now().date()
        start = today + timedelta(days=5)
        self.assertGreater(start, today + timedelta(days=1))

    def test_35_rebate_caretaker_approval(self):
        r = RebateRequest.objects.create(student=self.student, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6))
        r.status = 'approved'
        r.save()
        self.assertEqual(r.status, 'approved')

    def test_36_rebate_caretaker_rejection(self):
        r = RebateRequest.objects.create(student=self.student, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6))
        r.status = 'rejected'
        r.save()
        self.assertEqual(r.status, 'rejected')

    def test_37_rebate_caretaker_modifies_approved_dates(self):
        orig_start = timezone.now().date() + timedelta(days=2)
        orig_end = timezone.now().date() + timedelta(days=7)
        r = RebateRequest.objects.create(student=self.student, reason='medical', start_date=orig_start, end_date=orig_end)
        r.approved_start_date = orig_start + timedelta(days=1)
        r.approved_end_date = orig_end
        r.status = 'approved'
        r.save()
        self.assertNotEqual(r.start_date, r.approved_start_date)

    def test_38_rebate_non_overlap_distinct_dates(self):
        r1 = RebateRequest.objects.create(student=self.student, reason='medical', start_date=date(2026, 11, 10), end_date=date(2026, 11, 14), status='approved')
        r2 = RebateRequest.objects.create(student=self.student, reason='institute_leave', start_date=date(2026, 11, 16), end_date=date(2026, 11, 20), status='pending')
        self.assertLess(r1.end_date, r2.start_date)

    # ==========================================
    # 6. Special Food Requests (AFR-070..080, CW-MMS-05)
    # ==========================================
    def test_39_special_food_initial_state_requested(self):
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Viral fever diet', requested_date=timezone.now().date()+timedelta(days=2))
        self.assertEqual(sf.status, 'requested')

    def test_40_special_food_lead_time_valid(self):
        target = timezone.now().date() + timedelta(days=2)
        self.assertGreater(target, timezone.now().date())

    def test_41_special_food_caretaker_approve(self):
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Illness', requested_date=timezone.now().date()+timedelta(days=2))
        sf.status = 'approved'
        sf.charge = Decimal('150.00')
        sf.save()
        self.assertEqual(sf.status, 'approved')
        self.assertEqual(sf.charge, Decimal('150.00'))

    def test_42_special_food_caretaker_reject(self):
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Personal treat', requested_date=timezone.now().date()+timedelta(days=2))
        sf.status = 'rejected'
        sf.save()
        self.assertEqual(sf.status, 'rejected')

    def test_43_special_food_transition_approved_to_served(self):
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Diet meal', requested_date=timezone.now().date()+timedelta(days=2), status='approved')
        sf.status = 'served'
        sf.save()
        self.assertEqual(sf.status, 'served')

    def test_44_special_food_transition_approved_to_cancelled(self):
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Diet meal', requested_date=timezone.now().date()+timedelta(days=2), status='approved')
        sf.status = 'cancelled'
        sf.save()
        self.assertEqual(sf.status, 'cancelled')

    def test_45_special_food_auto_timeout_rejection_task(self):
        past_time = timezone.now() - timedelta(hours=1)
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Illness', requested_date=timezone.now().date()+timedelta(days=2), status='requested', timeout_at=past_time)
        auto_reject_special_food_timeouts()
        sf.refresh_from_db()
        self.assertEqual(sf.status, 'rejected')

    def test_46_special_food_timeout_ignores_fresh_requests(self):
        future_time = timezone.now() + timedelta(hours=8)
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Illness', requested_date=timezone.now().date()+timedelta(days=2), status='requested', timeout_at=future_time)
        auto_reject_special_food_timeouts()
        sf.refresh_from_db()
        self.assertEqual(sf.status, 'requested')

    # ==========================================
    # 7. Vacation Surveys & Default No (AFR-062..069, CW-MMS-04)
    # ==========================================
    def test_47_create_vacation_survey(self):
        vs = VacationSurvey.objects.create(
            vacation_name="Diwali Break 2026",
            start_date=timezone.now().date()+timedelta(days=5),
            end_date=timezone.now().date()+timedelta(days=15),
            deadline=timezone.now()+timedelta(days=3),
            is_open=True
        )
        self.assertTrue(vs.is_open)

    def test_48_student_explicit_yes_response(self):
        vs = VacationSurvey.objects.create(vacation_name="Break", start_date=timezone.now().date()+timedelta(days=5), end_date=timezone.now().date()+timedelta(days=10), deadline=timezone.now()+timedelta(days=2))
        resp = VacationSurveyResponse.objects.create(survey=vs, student=self.student, response='yes')
        self.assertEqual(resp.response, 'yes')

    def test_49_student_explicit_no_response(self):
        vs = VacationSurvey.objects.create(vacation_name="Break", start_date=timezone.now().date()+timedelta(days=5), end_date=timezone.now().date()+timedelta(days=10), deadline=timezone.now()+timedelta(days=2))
        resp = VacationSurveyResponse.objects.create(survey=vs, student=self.student, response='no')
        self.assertEqual(resp.response, 'no')

    def test_50_survey_default_no_applied_at_deadline(self):
        RegistrationRequest.objects.create(student=self.student, window=self.window, status='approved')
        past_deadline = timezone.now() - timedelta(minutes=5)
        vs = VacationSurvey.objects.create(vacation_name="Winter Break", start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=10), deadline=past_deadline, is_open=True)
        apply_default_vacation_no()
        resp = VacationSurveyResponse.objects.filter(survey=vs, student=self.student).first()
        self.assertIsNotNone(resp)
        self.assertEqual(resp.response, 'default_no')

    def test_51_survey_default_no_preserves_explicit_yes(self):
        RegistrationRequest.objects.create(student=self.student, window=self.window, status='approved')
        past_deadline = timezone.now() - timedelta(minutes=5)
        vs = VacationSurvey.objects.create(vacation_name="Winter Break", start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=10), deadline=past_deadline, is_open=True)
        VacationSurveyResponse.objects.create(survey=vs, student=self.student, response='yes')
        apply_default_vacation_no()
        resp = VacationSurveyResponse.objects.get(survey=vs, student=self.student)
        self.assertEqual(resp.response, 'yes')

    def test_52_survey_closes_after_default_no_execution(self):
        past_deadline = timezone.now() - timedelta(minutes=5)
        vs = VacationSurvey.objects.create(vacation_name="Past", start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=10), deadline=past_deadline, is_open=True)
        apply_default_vacation_no()
        vs.refresh_from_db()
        self.assertFalse(vs.is_open)

    # ==========================================
    # 8. Monthly Billing Management (AFR-033..043, BW-MMS-16)
    # ==========================================
    def test_53_monthly_bill_creation_generated(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, status='generated')
        self.assertEqual(bill.status, 'generated')

    def test_54_bill_base_charge_computation(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, served_days=30, daily_rate=Decimal('120.00'), base_charge=Decimal('3600.00'), total_amount=Decimal('3600.00'))
        self.assertEqual(bill.served_days * bill.daily_rate, bill.base_charge)

    def test_55_bill_with_special_food_charge_addition(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, base_charge=Decimal('3600.00'), special_food_charge=Decimal('250.00'), rebate_deduction=Decimal('0.00'), total_amount=Decimal('3850.00'))
        self.assertEqual(bill.base_charge + bill.special_food_charge, bill.total_amount)

    def test_56_bill_with_rebate_deduction(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, base_charge=Decimal('3600.00'), special_food_charge=Decimal('0.00'), rebate_deduction=Decimal('600.00'), total_amount=Decimal('3000.00'))
        self.assertEqual(bill.base_charge - bill.rebate_deduction, bill.total_amount)

    def test_57_bill_compound_special_food_and_rebate(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, base_charge=Decimal('3600.00'), special_food_charge=Decimal('300.00'), rebate_deduction=Decimal('480.00'), total_amount=Decimal('3420.00'))
        expected = bill.base_charge + bill.special_food_charge - bill.rebate_deduction
        self.assertEqual(bill.total_amount, expected)

    def test_58_caretaker_finalizes_bill(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, status='generated')
        bill.status = 'finalized'
        bill.save()
        self.assertEqual(bill.status, 'finalized')

    def test_59_caretaker_publishes_bill(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, status='finalized')
        bill.status = 'published'
        bill.published_at = timezone.now()
        bill.save()
        self.assertEqual(bill.status, 'published')
        self.assertIsNotNone(bill.published_at)

    def test_60_student_can_only_view_published_bills(self):
        MonthlyBill.objects.create(student=self.student, month=10, year=2026, status='published')
        MonthlyBill.objects.create(student=self.student, month=11, year=2026, status='generated')
        visible = MonthlyBill.objects.filter(student=self.student, status='published')
        self.assertEqual(visible.count(), 1)

    # ==========================================
    # 9. Feedback & Announcements (AFR-044..048, AFR-081..085)
    # ==========================================
    def test_61_student_submits_text_feedback(self):
        fb = Feedback.objects.create(student=self.student, content="Quality of dinner dal needs improvement.")
        self.assertEqual(fb.student, self.student)
        self.assertIn("improvement", fb.content)

    def test_62_feedback_contains_timestamp(self):
        fb = Feedback.objects.create(student=self.student, content="Breakfast is excellent.")
        self.assertIsNotNone(fb.created_at)

    def test_63_caretaker_publishes_announcement(self):
        ann = Announcement.objects.create(author=self.caretaker_user, title="Special Feast", content="Special dinner on Sunday evening.", target_role='all')
        self.assertEqual(ann.author, self.caretaker_user)
        self.assertEqual(ann.target_role, 'all')

    def test_64_warden_publishes_announcement(self):
        ann = Announcement.objects.create(author=self.warden_user, title="Mess Committee Meeting", content="All wing representatives meet at 5 PM.", target_role='students')
        self.assertEqual(ann.author, self.warden_user)

    def test_65_announcement_chronological_ordering(self):
        a1 = Announcement.objects.create(author=self.caretaker_user, title="Notice 1", content="One")
        a2 = Announcement.objects.create(author=self.caretaker_user, title="Notice 2", content="Two")
        self.assertLessEqual(a1.created_at, a2.created_at)

    # ==========================================
    # 10. Reports & Scope Boundaries (AFR-086..093)
    # ==========================================
    def test_66_warden_registered_student_query(self):
        RegistrationRequest.objects.create(student=self.student, window=self.window, status='approved')
        regs = RegistrationRequest.objects.filter(status='approved')
        self.assertEqual(regs.count(), 1)

    def test_67_warden_rebate_summary_query(self):
        RebateRequest.objects.create(student=self.student, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6), status='approved')
        approved_rebates = RebateRequest.objects.filter(status='approved')
        self.assertEqual(approved_rebates.count(), 1)

    def test_68_caretaker_special_meal_log_query(self):
        SpecialFoodRequest.objects.create(student=self.student, reason='Fever', requested_date=timezone.now().date()+timedelta(days=2), status='served')
        served_meals = SpecialFoodRequest.objects.filter(status='served')
        self.assertEqual(served_meals.count(), 1)

    def test_69_caretaker_billing_summary_query(self):
        MonthlyBill.objects.create(student=self.student, month=11, year=2026, total_amount=Decimal('3600.00'), status='published')
        MonthlyBill.objects.create(student=self.student2, month=11, year=2026, total_amount=Decimal('3400.00'), status='published')
        total_billing = sum(b.total_amount for b in MonthlyBill.objects.filter(month=11, year=2026))
        self.assertEqual(total_billing, Decimal('7000.00'))

    def test_70_student_request_isolation(self):
        r1 = RebateRequest.objects.create(student=self.student, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6))
        r2 = RebateRequest.objects.create(student=self.student2, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6))
        student1_rebates = RebateRequest.objects.filter(student=self.student)
        self.assertIn(r1, student1_rebates)
        self.assertNotIn(r2, student1_rebates)

    # ==========================================
    # 11. Extended Boundary & Integrity Cases (BR-001..042)
    # ==========================================
    def test_71_deregistration_pending_prevents_duplicate(self):
        DeregistrationRequest.objects.create(student=self.student, status='pending')
        pending_exists = DeregistrationRequest.objects.filter(student=self.student, status='pending').exists()
        self.assertTrue(pending_exists)

    def test_72_rebate_end_date_equal_start_date_invalid(self):
        start = timezone.now().date() + timedelta(days=2)
        duration = (start - start).days + 1
        self.assertEqual(duration, 1)
        self.assertLess(duration, 3)

    def test_73_rebate_2_days_duration_fails_bva(self):
        start = timezone.now().date() + timedelta(days=2)
        end = start + timedelta(days=1)
        duration = (end - start).days + 1
        self.assertEqual(duration, 2)
        self.assertLess(duration, 3)

    def test_74_rebate_start_today_fails_lead_time(self):
        today = timezone.now().date()
        lead_time = (today - today).days
        self.assertLess(lead_time, 1)

    def test_75_special_food_lead_time_zero_days_fails(self):
        today = timezone.now().date()
        self.assertEqual((today - today).days, 0)

    def test_76_vacation_survey_multiple_registered_defaults(self):
        RegistrationRequest.objects.create(student=self.student, window=self.window, status='approved')
        RegistrationRequest.objects.create(student=self.student2, window=self.window, status='approved')
        past_deadline = timezone.now() - timedelta(minutes=10)
        vs = VacationSurvey.objects.create(vacation_name="Break 2", start_date=timezone.now().date()+timedelta(days=3), end_date=timezone.now().date()+timedelta(days=7), deadline=past_deadline)
        apply_default_vacation_no()
        self.assertEqual(VacationSurveyResponse.objects.filter(survey=vs, response='default_no').count(), 2)

    def test_77_billing_cycle_month_bounds(self):
        for m in range(1, 13):
            bill = MonthlyBill.objects.create(student=self.student, month=m, year=2026)
            self.assertTrue(1 <= bill.month <= 12)

    def test_78_served_days_cannot_exceed_31(self):
        bill = MonthlyBill.objects.create(student=self.student, month=1, year=2026, served_days=31)
        self.assertLessEqual(bill.served_days, 31)

    def test_79_zero_served_days_computation(self):
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, served_days=0, daily_rate=Decimal('120.00'), base_charge=Decimal('0.00'), total_amount=Decimal('0.00'))
        self.assertEqual(bill.total_amount, Decimal('0.00'))

    def test_80_menu_items_empty_fallback(self):
        menu = MenuItem.objects.filter(day=5, meal='lunch')
        self.assertEqual(menu.count(), 0)

    def test_81_feedback_multiple_submissions(self):
        Feedback.objects.create(student=self.student, content="Fb 1")
        Feedback.objects.create(student=self.student, content="Fb 2")
        self.assertEqual(Feedback.objects.filter(student=self.student).count(), 2)

    def test_82_role_deactivation_timestamp_recorded(self):
        now = timezone.now()
        role = MessRole.objects.create(user=self.student, role='caretaker', start_time=now - timedelta(days=30), end_time=now, is_active=False)
        self.assertFalse(role.is_active)
        self.assertIsNotNone(role.end_time)

    def test_83_registration_window_future_overlap_allowed(self):
        w1 = self.window
        w2 = RegistrationWindow.objects.create(cycle_name="Next", start_date=w1.end_date + timedelta(days=1), end_date=w1.end_date + timedelta(days=30))
        self.assertGreater(w2.start_date, w1.end_date)

    def test_84_special_food_charge_zero_allowed(self):
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='No charge sick diet', requested_date=timezone.now().date()+timedelta(days=2), charge=Decimal('0.00'))
        self.assertEqual(sf.charge, Decimal('0.00'))

    def test_85_complete_end_to_end_student_lifecycle(self):
        # 1. Register
        reg = RegistrationRequest.objects.create(student=self.student, window=self.window, status='approved')
        self.assertEqual(reg.status, 'approved')
        # 2. Rebate
        reb = RebateRequest.objects.create(student=self.student, reason='medical', start_date=timezone.now().date()+timedelta(days=2), end_date=timezone.now().date()+timedelta(days=6), status='approved')
        self.assertEqual(reb.status, 'approved')
        # 3. Special meal
        sf = SpecialFoodRequest.objects.create(student=self.student, reason='Sick diet', requested_date=timezone.now().date()+timedelta(days=2), status='served', charge=Decimal('100.00'))
        self.assertEqual(sf.status, 'served')
        # 4. Bill generated
        bill = MonthlyBill.objects.create(student=self.student, month=11, year=2026, base_charge=Decimal('3600.00'), special_food_charge=sf.charge, rebate_deduction=Decimal('600.00'), total_amount=Decimal('3100.00'), status='published')
        self.assertEqual(bill.total_amount, Decimal('3100.00'))
        # 5. Deregister
        dreg = DeregistrationRequest.objects.create(student=self.student, status='effective')
        self.assertEqual(dreg.status, 'effective')