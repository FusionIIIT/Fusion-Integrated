from django.db import models

from modules.oap.domain import nodues as rules


class NoDuesRequest(models.Model):
    student_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=80, choices=rules.STATE_CHOICES, default=rules.INITIAL_STATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    finalized_by_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    certificate_number = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"No-dues #{self.pk} (student {self.student_id}) - {self.status}"


class NoDuesClearance(models.Model):
    request = models.ForeignKey(
        NoDuesRequest, on_delete=models.CASCADE, related_name="clearances"
    )
    domain_code = models.CharField(
        max_length=30,
        choices=[(code, name) for code, name, _ in rules.AUTHORITIES],
    )
    result = models.CharField(
        max_length=30, choices=rules.RESULT_CHOICES, default=rules.RESULT_PENDING
    )
    remark = models.TextField(blank=True)
    recorded_by_id = models.IntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["request", "domain_code"],
                name="oap_nodues_one_row_per_domain",
            )
        ]

    def __str__(self):
        return f"{self.domain_code}: {self.result} (request {self.request_id})"
