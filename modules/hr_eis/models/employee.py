from django.db import models
from modules.hr_eis.contracts import EmploymentTypes, EmployeeStatus

class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code} - {self.name}"

class EmployeeProfile(models.Model):
    user_id = models.CharField(max_length=64, unique=True, db_index=True)
    employee_id = models.CharField(max_length=32, unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=30, choices=EmploymentTypes.CHOICES, default=EmploymentTypes.FACULTY)
    date_of_joining = models.DateField()
    date_of_birth = models.DateField()
    retirement_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=EmployeeStatus.CHOICES, default=EmployeeStatus.ACTIVE)
    is_hod = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee_id} - {self.full_name} ({self.department})"
