from django.db import models
from core.db.mixins import TimeStampedModel

class VacationSurvey(TimeStampedModel):
    title = models.CharField(max_length=120)
    vacation_start = models.DateField()
    vacation_end = models.DateField()
    response_deadline = models.DateTimeField()
    STATUS = (
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    )
    status = models.CharField(max_length=10, choices=STATUS, default='OPEN')
    created_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = 'mess_vacation_survey'
        constraints = [
            models.UniqueConstraint(fields=['created_by_user_id'], name='unique_created_by_user_id')
        ]

    def __str__(self):
        return self.title
