from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class Feedback(TimeStampedModel, UserScopedModel):
    text = models.TextField()

    class Meta:
        db_table = 'mess_feedback'
        indexes = [models.Index(fields=['created_at'])]

    def __str__(self):
        return f'Feedback by {self.user_id}: {self.text[:50]}'
