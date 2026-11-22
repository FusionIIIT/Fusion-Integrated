# modules/hr_eis/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class EmployeeProfile(models.Model):
    DESIGNATION_CHOICES = (
        ("PROFESSOR", "Professor"),
        ("ASSOC_PROF", "Associate Professor"),
        ("ASST_PROF", "Assistant Professor"),
        ("STAFF", "Technical / Administrative Staff"),
    )

    DEPARTMENT_CHOICES = (
        ("CSE", "Computer Science and Engineering"),
        ("ECE", "Electronics and Communication Engineering"),
        ("ME", "Mechanical Engineering"),
        ("DESIGN", "Design"),
        ("NS", "Natural Sciences"),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="eis_profile"
    )
    pf_number = models.CharField(max_length=50, unique=True, db_index=True)
    designation = models.CharField(max_length=50, choices=DESIGNATION_CHOICES)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    date_of_joining = models.DateField()
    about_me = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employee Profiles"
        ordering = ["pf_number"]

    def clean(self):
        super().clean()
        valid_designations = [choice[0] for choice in self.DESIGNATION_CHOICES]
        if self.designation and self.designation not in valid_designations:
            raise ValidationError(
                {"designation": f"Invalid designation: {self.designation}"}
            )

        valid_departments = [choice[0] for choice in self.DEPARTMENT_CHOICES]
        if self.department and self.department not in valid_departments:
            raise ValidationError(
                {"department": f"Invalid department: {self.department}"}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.pf_number}) - {self.designation}"


class WorkExperience(models.Model):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="experiences"
    )
    organization = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Work Experience"
        verbose_name_plural = "Work Experiences"
        ordering = ["-start_date"]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.position} at {self.organization}"
