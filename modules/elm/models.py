from django.db import models

from django.utils.translation import gettext_lazy as _



class LeaveCategory(models.Model):

    code = models.CharField(max_length=3, unique=True,
verbose_name=_('Code'))

    name = models.CharField(max_length=100,
verbose_name=_('Name'))



    class Meta:

        verbose_name = _('Leave Category')

        verbose_name_plural = _('Leave Categories')



    def __str__(self):

        return self.name



class LeaveApplication(models.Model):

    STATUS_CHOICES = [

        ('draft', _('Draft')),

        ('submitted', _('Submitted')),

        ('approved', _('Approved')),

        ('rejected', _('Rejected')),

    ]



    employee = models.ForeignKey('directory.UserRef',
on_delete=models.CASCADE, verbose_name=_('Employee'))

    category = models.ForeignKey(LeaveCategory,
on_delete=models.CASCADE, verbose_name=_('Category'))

    start_date = models.DateField(verbose_name=_('Start Date'))

    end_date = models.DateField(verbose_name=_('End Date'))

    status = models.CharField(max_length=10,
choices=STATUS_CHOICES, default='draft',
verbose_name=_('Status'))



    class Meta:

        verbose_name = _('Leave Application')

        verbose_name_plural = _('Leave Applications')



    def __str__(self):

        return f"{self.employee} - {self.category} -
{self.status}"