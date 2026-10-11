from django.db import models
from django.utils.translation import gettext as _

class Leave(models.Model):
    """
    Model representing a leave request.
    """
    LEAVE_CATEGORIES = [
        ('CL', _('Casual Leave')),
        ('RH', _('Restricted Holiday')),
        ('SCL', _('Special Casual Leave')),
        ('EL', _('Extra Leave')),
        ('COL', _('Compensatory Off Leave')),
        ('VL', _('Vacation Leave')),
    ]

    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('under_review', _('Under Review')),
        ('shortlisted', _('Shortlisted')),
        ('interview_scheduled', _('Interview Scheduled')),
        ('selected', _('Selected')),
        ('rejected', _('Rejected')),
        ('withdrawn', _('Withdrawn')),
        ('auto_withdrawn', _('Auto Withdrawn')),
        ('offer_issued', _('Offer Issued')),
        ('offer_accepted', _('Offer Accepted')),
        ('offer_declined', _('Offer Declined')),
    ]

    employee = models.ForeignKey('directory.UserRef', on_delete=models.PROTECT, verbose_name=_('Employee'))
    category = models.CharField(max_length=3, choices=LEAVE_CATEGORIES, verbose_name=_('Leave Category'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    reason = models.TextField(verbose_name=_('Reason for Leave'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name=_('Status'))

    class Meta:
        verbose_name = _('Leave')
        verbose_name_plural = _('Leaves')

    def __str__(self):
        return f'{self.employee.user.name} - {self.get_category_display()} from {self.start_date} to {self.end_date}'
