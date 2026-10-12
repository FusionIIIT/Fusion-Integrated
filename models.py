from django.db import models
from django.contrib.auth.models import User

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    designation = models.CharField(max_length=100)
    organizational_unit = models.CharField(max_length=100)
    unit_head = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='subordinates')

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

class Entitlement(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

class LeaveApplication(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=100, choices=[
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('under_review', 'Under review'), ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview scheduled'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'),
        ('auto_withdrawn', 'Withdrawn automatically'),
        ('offer_issued', 'Offer issued'), ('offer_accepted', 'Offer accepted'),
        ('offer_declined', 'Offer declined'), ('offer_expired', 'Offer expired'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LeaveApplicationTransition(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=100, choices=[
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('under_review', 'Under review'), ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview scheduled'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'),
        ('auto_withdrawn', 'Withdrawn automatically'),
        ('offer_issued', 'Offer issued'), ('offer_accepted', 'Offer accepted'),
        ('offer_declined', 'Offer declined'), ('offer_expired', 'Offer expired'),
    ])
    transitioned_at = models.DateTimeField(auto_now_add=True)
