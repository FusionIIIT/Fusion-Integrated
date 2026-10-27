from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CL = 'CL', _('Casual Leave')
    RH = 'RH', _('Restricted Holiday')
    SCL = 'SCL', _('Special Casual Leave')
    EL = 'EL', _('Earned Leave')
    COL = 'COL', _('Compensatory Off Leave')
    VL = 'VL', _('Vacation Leave')


class LeaveStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    CANCELLED = 'cancelled', _('Cancelled')
    WITHDRAWN = 'withdrawn', _('Withdrawn')


class LeaveDayPart(models.TextChoices):
    FULL_DAY = 'full_day', _('Full day')
    FIRST_HALF = 'first_half', _('First half')
    SECOND_HALF = 'second_half', _('Second half')


# user_id is the IAM user id, not a ForeignKey (ADR-0013).
class LeaveRequest(UserScopedModel, TimeStampedModel):
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    day_part = models.CharField(
        max_length=16,
        choices=LeaveDayPart.choices,
        default=LeaveDayPart.FULL_DAY,
    )
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
            models.CheckConstraint(
                condition=(
                    models.Q(day_part=LeaveDayPart.FULL_DAY)
                    | (
                        models.Q(category=LeaveCategory.CL)
                        & models.Q(start_date=models.F('end_date'))
                        & models.Q(day_part__in=(
                            LeaveDayPart.FIRST_HALF,
                            LeaveDayPart.SECOND_HALF,
                        ))
                    )
                ),
                name='elm_cl_half_day_single_date',
            ),
        ]

    def __str__(self):
        return (f'{self.user_id} - {self.get_category_display()} '
                f'from {self.start_date} to {self.end_date}')


class LeaveRequestEvent(models.Model):
    class Type(models.TextChoices):
        SUBMITTED = 'submitted', _('Submitted')
        WITHDRAWN = 'withdrawn', _('Withdrawn')

    request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name='events',
    )
    event_type = models.CharField(max_length=20, choices=Type.choices)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']

    def __str__(self):
        return f'{self.request_id} - {self.event_type}'
