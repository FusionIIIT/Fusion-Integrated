from django.db import models

from modules.oap.domain import seminar as rules


class SeminarRequest(models.Model):
    student_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=80, choices=rules.STATE_CHOICES, default=rules.INITIAL_STATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    scheduled_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Seminar #{self.pk} (student {self.student_id}) - {self.status}"
