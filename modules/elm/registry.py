from django.contrib.auth.models import Permission

class LeaveELMPermissions:
    """
    Registry for Leave ELM Permissions
    """
    ROLES = {
        'Employee': 'can_view_leave_applications',
        'Leave Approver': 'can_approve_leave_applications',
    }

    @classmethod
    def get_permissions(cls, role):
        """
        Get permissions for a given role
        """
        return cls.ROLES.get(role, None)

class LeaveELMNavigationItems:
    """
    Registry for Leave ELM Navigation Items
    """
    NAV_ITEMS = {
        'leave_applications': {
            'name': 'Leave Applications',
            'path': '/leave-applications/',
            'permissions': ['can_view_leave_applications'],
        },
        'create_leave_application': {
            'name': 'Create Leave Application',
            'path': '/leave-applications/create/',
            'permissions': ['can_approve_leave_applications'],
        },
    }

    @classmethod
    def get_nav_items(cls):
        """
        Get navigation items
        """
        return cls.NAV_ITEMS