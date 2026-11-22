"""Department entity model."""

from django.db import models


class Department(models.Model):
    code = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    core_policies = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_department"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
