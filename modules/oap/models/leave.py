from django.db import models

from modules.oap.domain import leave as rules


class LeaveApplication(models.Model):
    student_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=80, choices=rules.STATE_CHOICES, default=rules.INITIAL_STATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    supporting_document = models.FileField(upload_to="oap/leave/", blank=True)
    decided_by_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remark = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Leave #{self.pk} (student {self.student_id}) - {self.status}"
