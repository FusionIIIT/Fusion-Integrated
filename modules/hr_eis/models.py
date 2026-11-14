# modules/hr_eis/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class EmployeeProfile(models.Model):
    DESIGNATION_CHOICES = (
        ('PROFESSOR', 'Professor'),
        ('ASSOC_PROF', 'Associate Professor'),
        ('ASST_PROF', 'Assistant Professor'),
        ('STAFF', 'Technical / Administrative Staff'),
    )
    
    DEPARTMENT_CHOICES = (
        ('CSE', 'Computer Science and Engineering'),
        ('ECE', 'Electronics and Communication Engineering'),
        ('ME', 'Mechanical Engineering'),
        ('DESIGN', 'Design'),
        ('NS', 'Natural Sciences'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='eis_profile')
    pf_number = models.CharField(max_length=50, unique=True)
    designation = models.CharField(max_length=50, choices=DESIGNATION_CHOICES)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    date_of_joining = models.DateField()
    about_me = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.pf_number}) - {self.designation}"


class WorkExperience(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='experiences')
    organization = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.position} at {self.organization}"