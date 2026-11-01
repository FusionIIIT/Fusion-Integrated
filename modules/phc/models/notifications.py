"""In-system notification events (AFR-PHC-023, AFR-PHC-026, AFR-PHC-030; BR-PHC-07, 11, 13)."""
from django.db import models


class PHCNotification(models.Model):
    TYPE_CHOICES = [
        ("LOW_STOCK", "Low Stock Alert"),
        ("REQUISITION_DECISION", "Requisition Decision"),
        ("REIMBURSEMENT_STATUS", "Reimbursement Status"),
    ]

    recipient_user_id = models.IntegerField(db_index=True)
    notification_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "phc_notifications"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.notification_type}] To {self.recipient_user_id}: {self.title}"
