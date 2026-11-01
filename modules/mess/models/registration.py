from django.db import models
from django.db.models import F, Q
from core.db.mixins import TimeStampedModel, UserScopedModel


class RegistrationWindow(TimeStampedModel):
    title = models.CharField(max_length=120)
    opens_on = models.DateField()
    closes_on = models.DateField()
    status = models.CharField(max_length=10, choices=[('OPEN', 'OPEN'), ('CLOSED', 'CLOSED')], default='OPEN')

    class Meta:
        db_table = 'mess_registration_window'


class RegistrationRequest(TimeStampedModel, UserScopedModel):
    window = models.ForeignKey(RegistrationWindow, on_delete=models.PROTECT, related_name='requests')
    status = models.CharField(max_length=10, choices=[('PENDING', 'PENDING'), ('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED')], default='PENDING')
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mess_registration_request'
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'window'], name='unique_registration_request')
        ]

    def __str__(self):
        return f'RegistrationRequest {self.id}'


class DeregistrationRequest(TimeStampedModel, UserScopedModel):
    status = models.CharField(max_length=30, choices=[('PENDING', 'PENDING'), ('APPROVED_AWAITING_EFFECTIVE', 'APPROVED_AWAITING_EFFECTIVE'), ('REJECTED', 'REJECTED'), ('EFFECTIVE', 'EFFECTIVE')], default='PENDING')
    reason = models.CharField(max_length=300, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    effective_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'mess_deregistration_request'
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'effective_on'], name='unique_deregistration_request')
        ]

    def __str__(self):
        return f'DeregistrationRequest {self.id}'
