"""Leave Management Django app configuration.

Follows placement module pattern: AppConfig with ready() for check
registration. MODULE/NAV_ITEMS with permission filtering.
"""
from django.apps import AppConfig


class LeaveConfig(AppConfig):
    """Leave Management app configuration."""
    name = "modules.leave"
    verbose_name = "Employee Leave Management"

    def ready(self):
        """Register system checks and other initialization."""
        # Import here to avoid circular imports
        from modules.leave import checks
        from modules.leave import permissions
        from modules.leave import registry

        # Run system checks
        checks.ready()

        # Register module and navigation items
        registry.ready()
