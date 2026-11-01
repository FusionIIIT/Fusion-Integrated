from django.db import models
from django.db.models import F, Q

class RequestTransition(models.Model):
    request_type = models.CharField(max_length=24)
    request_id = models.IntegerField()
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mess_request_transition"
        indexes = [
            models.Index(fields=['request_type', 'request_id']),
        ]

    def __str__(self):
        return f"RequestTransition {self.request_id}: {self.from_status} -> {self.to_status}"
