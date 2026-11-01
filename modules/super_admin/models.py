from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser
import json # Import json if you need to use JSONField effectively in older Django versions, though Django's JSONField handles serialization.

# Assuming you might need a custom base model or a context where these models belong
# For demonstration, we'll put them directly in a conceptual app module.

# --- Model Definitions ---

class UserAccount(models.Model):
    """
    Represents a primary user account within the Fusion ERP Super Admin module.
    """
    institute_id = models.CharField(max_length=64, unique=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)

    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff')
    ]
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deactivated', 'Deactivated'),
        ('archived', 'Archived')
    ]
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"User: {self.username} ({self.get_user_type_display()})"

    class Meta:
        verbose_name = "UserAccount"
        verbose_name_plural = "UserAccounts"


class RoleAssignment(models.Model):
    """
    Links a UserAccount to specific roles over a defined period.
    """
    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    role_name = models.CharField(max_length=64)
    assigned_by = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired')
    ]
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} assigned {self.role_name} ({self.status.capitalize()})"

    class Meta:
        verbose_name = "RoleAssignment"
        verbose_name_plural = "RoleAssignments"


class SystemAuditLog(models.Model):
    """
    Tracks significant actions performed within the system for auditing purposes.
    """
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=64)
    target = models.CharField(max_length=255)
    # Django's built-in JSONField (available in modern Django versions) is used here.
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit Log - {self.action} by {self.actor_username} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "SystemAuditLog"
        verbose_name_plural = "SystemAuditLogs"