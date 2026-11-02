from django.db import models


class ArchiveLog(models.Model):
    ACTION_CHOICES = [
        ("archive", "Archived"),
        ("alumni", "Marked Alumni"),
        ("restore", "Restored"),
    ]
    USER_TYPE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
    ]

    username = models.CharField(max_length=150, db_index=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    previous_status = models.CharField(max_length=50, blank=True, default="")
    new_status = models.CharField(max_length=50, blank=True, default="")
    performed_by = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "archive_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.username} ({self.user_type})"
