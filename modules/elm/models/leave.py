from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CL = 'CL', _('Casual Leave')
    RH = 'RH', _('Restricted Holiday')
    SCL = 'SCL', _('Special Conduct Leave')
    EL = 'EL', _('Earned Leave')
    COL = 'COL', _('Compensatory Off Leave')
    VL = 'VL', _('Vacation Leave')


class LeaveStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    CANCELLED = 'cancelled', _('Cancelled')


# user_id is the IAM user id, not a ForeignKey (ADR-0013).
class LeaveRequest(UserScopedModel, TimeStampedModel):
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LeaveStatus.choices,
                              default=LeaveStatus.PENDING)

    class Meta:
        verbose_name = _('Leave Request')
        verbose_name_plural = _('Leave Requests')
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='elm_leave_end_not_before_start'),
        ]

    def __str__(self):
        return (f'{self.user_id} - {self.get_category_display()} '
                f'from {self.start_date} to {self.end_date}')
