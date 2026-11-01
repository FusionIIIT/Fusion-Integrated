"""Django app configuration for Employee Leave Management module."""

from django.apps import AppConfig


class LeaveElmConfig(AppConfig):
    """Configuration for the Employee Leave Management module.

    This module handles leave entitlements, applications, approvals, and substitute coverage.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.leave_elm"
    label = "leave_elm"
    verbose_name = "Employee Leave Management"
