from django.db import models
from django.utils.translation import gettext as _

class LeaveType(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))

    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    employee = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name=_('Employee'))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, verbose_name=_('Leave Type'))
    balance = models.FloatField(verbose_name=_('Balance'))

    def __str__(self):
        return f'{self.employee} - {self.leave_type}'

class LeaveApplication(models.Model):
    STATUS_CHOICES = (
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    )

    employee = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name=_('Employee'))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, verbose_name=_('Leave Type'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='draft', verbose_name=_('Status'))

    def __str__(self):
        return f'{self.employee} - {self.leave_type} - {self.start_date} - {self.end_date}'

class LeaveSubstitute(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, verbose_name=_('Application'))
    substitute = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name=_('Substitute'))

    def __str__(self):
        return f'{self.application} - {self.substitute}'

class LeaveApproval(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, verbose_name=_('Application'))
    approver = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name=_('Approver'))
    approved_date = models.DateField(verbose_name=_('Approved Date'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return f'{self.application} - {self.approver} - {self.approved_date}'
