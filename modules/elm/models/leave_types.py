from django.db.models import CharField, TextField, BooleanField
from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    code = CharField(max_length=20, unique=True)
    name = CharField(max_length=50)
    description = TextField(blank=True)
    is_active = BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"

    def __str__(self):
        return self.name
