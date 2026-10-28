"""
Leave Management - Policy Models
Django models for leave policy configuration.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeavePolicyParameter(models.Model):
    """
    Singleton/per-category annual entitlements, carry-forward caps, and SLA thresholds.
    (BR-EL-030, BR-EL-038)
    """
    
    # Category options
    CATEGORIES = [
        ('cl', 'Casual Leave'),
        ('rh', 'Half-Sick Leave'),
        ('scl', 'Sick Leave'),
        ('el', 'Earned Leave'),
        ('vl', 'Vacation Leave'),
        ('col', 'Compensatory Leave'),
    ]
    
    # Transaction types
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('deduction', 'Deduction'),
        ('reversal', 'Reversal'),
        ('vl_conversion', 'VL Conversion'),
        ('resumption_adj', 'Resumption Adjustment'),
    ]
    
    category = models.CharField(
        max_length=10,
        choices=CATEGORIES,
        unique=True
    )
    
    # Annual entitlements
    annual_entitlement = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Carry-forward settings
    carry_forward_enabled = models.BooleanField(default=False)
    carry_forward_max = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # SLA thresholds
    sla_hours = models.PositiveIntegerField(
        default=24,  # 24 hours in default
        help_text='SLA time in hours for approval'
    )
    sla_escalation_hours = models.PositiveIntegerField(
        default=48,
        help_text='Escalation threshold in hours'
    )
    
    # Staff type differentiation
    is_faculty = models.BooleanField(
        default=False,
        help_text='True for faculty-specific entitlements'
    )
    
    # Override settings for faculty
    faculty_annual_entitlement = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        verbose_name = 'Leave Policy Parameter'
        verbose_name_plural = 'Leave Policy Parameters'
        ordering = ['category']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.annual_entitlement} days"


class HolidayCalendar(models.Model):
    """
    Holiday calendar for a given year.
    (BR-EL-031)
    """
    
    name = models.CharField(
        max_length=255,
        help_text='Holiday name (e.g., Eid ul-Fitr)'
    )
    
    date = models.DateField(
        help_text='Holiday date'
    )
    
    year = models.IntegerField(
        help_text='Year this holiday applies to'
    )
    
    is_rh = models.BooleanField(
        default=False,
        help_text='If True, this holiday counts as Half-Sick Leave (RH) day'
    )
    
    is_published = models.BooleanField(
        default=False,
        help_text='Whether this calendar is published to employees'
    )
    
    is_closed = models.BooleanField(
        default=False,
        help_text='If True, exclude from leave calculations'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Additional notes about this holiday'
    )
    
    class Meta:
        verbose_name = 'Holiday Calendar'
        verbose_name_plural = 'Holiday Calendars'
        ordering = ['-year', 'date']
        unique_together = ['year', 'date']
    
    def __str__(self):
        return f"{self.name} - {self.date} ({self.year}) - RH: {self.is_rh}"
