from django.db import models

from modules.oap.domain import bonafide as rules


class BonafideRequest(models.Model):
    student_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=80, choices=rules.STATE_CHOICES, default=rules.INITIAL_STATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    purpose = models.CharField(max_length=200, blank=True)
    decided_by_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remark = models.TextField(blank=True)
    certificate_number = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Bonafide #{self.pk} (student {self.student_id}) - {self.status}"
