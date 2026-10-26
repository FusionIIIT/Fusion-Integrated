from django.db import models
from django.utils.translation import gettext as _
from django_extensions.db.models import TimeStampedModel

class LeaveType(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Leave Type"))
    description = models.TextField(verbose_name=_("Description"))

    def __str__(self):
        return self.name

class LeaveBalance(TimeStampedModel):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.IntegerField(default=0, verbose_name=_("Leave Balance"))

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name}"

class LeaveApplication(TimeStampedModel):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    station_leave = models.BooleanField(default=False, verbose_name=_("Station Leave"))
    substitute = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='substitute', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} - {self.start_date} - {self.end_date}"