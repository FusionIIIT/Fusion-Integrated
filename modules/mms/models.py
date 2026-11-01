from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class MessRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('caretaker', 'Caretaker'), ('warden', 'Warden')])
    is_active = models.BooleanField(default=True)

class RegistrationWindow(models.Model):
    cycle_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True)

class RegistrationRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    window = models.ForeignKey(RegistrationWindow, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending') # pending, approved, rejected
    created_at = models.DateTimeField(auto_now_add=True)

class DeregistrationRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=30, default='pending') # pending, approved, effective, rejected
    effective_date = models.DateField(null=True, blank=True)

class MenuItem(models.Model):
    day = models.IntegerField() # 0-6
    meal = models.CharField(max_length=20) # breakfast, lunch, dinner
    items = models.TextField()

class RebateRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=50)
    explanation = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, default='pending')

class SpecialFoodRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    requested_date = models.DateField()
    status = models.CharField(max_length=20, default='requested') # requested, approved, rejected, served, cancelled
    charge = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)