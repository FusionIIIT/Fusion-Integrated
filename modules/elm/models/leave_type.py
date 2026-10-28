from django.db import models

class LeaveType(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"], name="leave_type_code_idx"),
        ]

    def __str__(self):
        return self.name
