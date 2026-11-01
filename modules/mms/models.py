from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# 1. Operational Roles & Boundaries (MMS-UC-001)
class MessRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mms_roles')
    role = models.CharField(max_length=20, choices=[('caretaker', 'Caretaker'), ('warden', 'Warden')])
    is_active = models.BooleanField(default=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

# 2. Registration & Deregistration (MMS-UC-002..006, MMS-UC-027)
class RegistrationWindow(models.Model):
    cycle_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True)

    def is_currently_active(self):
        today = timezone.now().date()
        return self.is_open and (self.start_date <= today <= self.end_date)

class RegistrationRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_registrations')
    window = models.ForeignKey(RegistrationWindow, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')  # pending, approved, rejected
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

class DeregistrationRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_deregistrations')
    status = models.CharField(max_length=30, default='pending')  # pending, approved_awaiting, effective, rejected
    decision_date = models.DateField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

# 3. Weekly Menu (MMS-UC-008..009)
class MenuItem(models.Model):
    day = models.IntegerField()  # 0 to 6
    meal = models.CharField(max_length=20)  # breakfast, lunch, dinner
    items = models.TextField()

# 4. Rebates (MMS-UC-014..015)
class RebateRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_rebates')
    reason = models.CharField(max_length=50)  # medical, institute_leave, family_function, other
    explanation = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    approved_start_date = models.DateField(null=True, blank=True)
    approved_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')  # pending, approved, rejected
    created_at = models.DateTimeField(auto_now_add=True)

# 5. Special Food Arrangement (MMS-UC-019..021, MMS-UC-029)
class SpecialFoodRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='special_food_requests')
    reason = models.TextField()
    requested_date = models.DateField()
    status = models.CharField(max_length=20, default='requested')  # requested, approved, rejected, served, cancelled
    charge = models.DecimalField(max_digits=7, decimal_places=2, default=0.0)
    timeout_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

# 6. Vacation Continuity Surveys (MMS-UC-016..018, MMS-UC-028, MMS-UC-031)
class VacationSurvey(models.Model):
    vacation_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    deadline = models.DateTimeField()
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class VacationSurveyResponse(models.Model):
    survey = models.ForeignKey(VacationSurvey, on_delete=models.CASCADE, related_name='responses')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    response = models.CharField(max_length=15, default='no')  # yes, no, default_no
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('survey', 'student')

# 7. Monthly Billing (MMS-UC-010..011, MMS-UC-030)
class MonthlyBill(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_bills')
    month = models.IntegerField()  # 1 to 12
    year = models.IntegerField()
    served_days = models.IntegerField(default=30)
    daily_rate = models.DecimalField(max_digits=6, decimal_places=2, default=120.0)
    base_charge = models.DecimalField(max_digits=8, decimal_places=2, default=3600.0)
    special_food_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    rebate_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=3600.0)
    status = models.CharField(max_length=20, default='generated')  # generated, finalized, published
    published_at = models.DateTimeField(null=True, blank=True)

# 8. Feedback & Announcements (MMS-UC-012..013, MMS-UC-022..023)
class Feedback(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Announcement(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_role = models.CharField(max_length=20, default='all')  # all, students
    created_at = models.DateTimeField(auto_now_add=True)