from django.db import models
from modules.hr_eis.models.employee import EmployeeProfile
from modules.hr_eis.contracts import AppraisalStatus

class AppraisalCycle(models.Model):
    year = models.CharField(max_length=20, unique=True)
    is_open = models.BooleanField(default=True)
    submission_deadline = models.DateField()
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Appraisal Cycle {self.year} (Open: {self.is_open})"

class AppraisalRecord(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="appraisals")
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name="records")
    self_assessment = models.TextField()
    assigned_reviewer = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_appraisals")
    reviewer_comments = models.TextField(blank=True, default="")
    hod_remarks = models.TextField(blank=True, default="")
    director_remarks = models.TextField(blank=True, default="")
    overall_rating = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=30, choices=AppraisalStatus.CHOICES, default=AppraisalStatus.DRAFT, db_index=True)
    is_immutable = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("employee", "cycle")

    def __str__(self):
        return f"Appraisal #{self.id} ({self.employee.employee_id} - {self.cycle.year} [{self.status}])"
