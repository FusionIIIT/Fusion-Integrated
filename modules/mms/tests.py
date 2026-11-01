from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import RegistrationWindow, RegistrationRequest, RebateRequest, SpecialFoodRequest, MonthlyBill

User = get_user_model()

class MMSTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_student", password="password123")
        self.window = RegistrationWindow.objects.create(
            cycle_name="Test Cycle 2026",
            start_date=timezone.now().date() - timedelta(days=1),
            end_date=timezone.now().date() + timedelta(days=20),
            is_open=True
        )

    def test_registration_request_creation(self):
        reg = RegistrationRequest.objects.create(student=self.user, window=self.window)
        self.assertEqual(reg.status, 'pending')

    def test_rebate_request_creation(self):
        rebate = RebateRequest.objects.create(
            student=self.user,
            reason='medical',
            start_date=timezone.now().date() + timedelta(days=2),
            end_date=timezone.now().date() + timedelta(days=6)
        )
        self.assertEqual(rebate.status, 'pending')

    def test_special_food_creation(self):
        sf = SpecialFoodRequest.objects.create(
            student=self.user,
            reason='Medical recovery',
            requested_date=timezone.now().date() + timedelta(days=1)
        )
        self.assertEqual(sf.status, 'requested')

    def test_monthly_bill_default_generation(self):
        bill = MonthlyBill.objects.create(
            student=self.user,
            month=11,
            year=2026,
            total_amount=3600.0,
            status='generated'
        )
        self.assertEqual(bill.total_amount, 3600.0)