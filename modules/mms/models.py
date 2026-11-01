from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

User = settings.AUTH_USER_MODEL

class MessRole(models.TextChoices):
    CARETAKER = 'caretaker', 'Mess Caretaker'
    WARDEN = 'warden', 'Mess Warden'

class RoleAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mms_roles')
    role = models.CharField(max_length=20, choices=MessRole.choices)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['role', 'is_active'])]

    def __str__(self):
        return f"{self.user} - {self.role} ({'Active' if self.is_active else 'Inactive'})"


class RegistrationWindow(models.Model):
    cycle_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_currently_active(self):
        today = timezone.now().date()
        return self.is_open and (self.start_date <= today <= self.end_date)


class RegistrationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'

class RegistrationRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_registrations')
    window = models.ForeignKey(RegistrationWindow, on_delete=models.CASCADE, related_name='requests')
    status = models.CharField(max_length=20, choices=RegistrationStatus.choices, default=RegistrationStatus.PENDING)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class DeregistrationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED_AWAITING_EFFECTIVE = 'approved_awaiting', 'Approved - Awaiting Effective Date'
    EFFECTIVE = 'effective', 'Effective / Deregistered'
    REJECTED = 'rejected', 'Rejected'

class DeregistrationRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_deregistrations')
    status = models.CharField(max_length=30, choices=DeregistrationStatus.choices, default=DeregistrationStatus.PENDING)
    decision_date = models.DateField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MealType(models.TextChoices):
    BREAKFAST = 'breakfast', 'Breakfast'
    LUNCH = 'lunch', 'Lunch'
    DINNER = 'dinner', 'Dinner'

class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'

class MenuItem(models.Model):
    day = models.IntegerField(choices=DayOfWeek.choices)
    meal = models.CharField(max_length=20, choices=MealType.choices)
    items = models.TextField(help_text="Comma-separated or JSON list of dishes")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('day', 'meal')


class RebateReason(models.TextChoices):
    MEDICAL = 'medical', 'Medical'
    INSTITUTE_LEAVE = 'institute_leave', 'Institute Leave'
    FAMILY_FUNCTION = 'family_function', 'Family Function'
    OTHER = 'other', 'Other'

class RebateStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'

class RebateRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mess_rebates')
    reason = models.CharField(max_length=30, choices=RebateReason.choices)
    explanation = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    approved_start_date = models.DateField(null=True, blank=True)
    approved_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=RebateStatus.choices, default=RebateStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def effective_duration(self):
        s = self.approved_start_date or self.start_date
        e = self.approved_end_date or self.end_date
        return (e - s).days + 1


class SpecialFoodStatus(models.TextChoices):
    REQUESTED = 'requested', 'Requested'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    SERVED = 'served', 'Served'
    CANCELLED = 'cancelled', 'Cancelled'

class SpecialFoodRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='special_food_requests')
    reason = models.TextField()