"""Leave Management Django app configuration.

Follows placement module pattern: AppConfig with ready() for check
registration. MODULE/NAV_ITEMS with permission filtering.
"""
from django.apps import AppConfig


class LeaveConfig(AppConfig):
    """Leave Management app configuration."""
    name = "modules.leave"
    label = "leave"
    verbose_name = "Employee Leave Management"
