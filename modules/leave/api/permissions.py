"""Leave Management API permissions.

Follows placement module pattern: permission classes in api/permissions.py,
service logic in services/permissions.py.
"""
from __future__ import annotations

from rest_framework import permissions
from rest_framework.request import Request


class LeaveModulePermission(permissions.BasePermission):
    """Permission class for leave module operations."""
    
    def has_permission(self, request: Request) -> bool:
        """Check if user has module grant."""
        from fusion_auth.permissions import HasModuleGrant
        
        return HasModuleGrant("leave_management").has_permission(request)
    
    def has_object_permission(self, request: Request, view, obj) -> bool:
        """Check if user has permission on specific object."""
        from modules.leave.api.permissions import ScopedCollection
        
        # Check module permission
        if not self.has_permission(request):
            return False
        
        # Check specific permission for the object type
        permission_classes = view.permission_classes
        if permission_classes and hasattr(permission_classes[0], 'get_object_permission'):
            return permission_classes[0].get_object_permission(request, view, obj)
        
        return True


class LeaveRequestPermission(permissions.BasePermission):
    """Permission class for leave request operations."""
    
    PERMISSIONS = {
        "view": "leave_management.leave.view",
        "create": "leave_management.leave.create",
        "update": "leave_management.leave.view",
        "destroy": "leave_management.leave.view",
        "approve": "leave_management.leave.approve",
        "cancel": "leave_management.leave.cancel",
        "resumefromresigned": "leave_management.leave.view",
    }
    
    def has_permission(self, request: Request) -> bool:
        """Check if user has permission."""
        from fusion_auth.permissions import HasPermission
        
        return HasPermission(self.PERMISSIONS.get(request.method.lower(), "view")).has_permission(request)
    
    def has_object_permission(self, request: Request, view, obj) -> bool:
        """Check if user has permission on specific object."""
        # Check if user owns the object
        if obj.user_id != request.user.id:
            return False
        
        # Check permission
        return self.has_permission(request)


class LeaveBalancePermission(permissions.BasePermission):
    """Permission class for leave balance operations."""
    
    PERMISSIONS = {
        "view": "leave_management.leave.balance.view",
        "create": "leave_management.leave.balance.view",
        "update": "leave_management.leave.balance.view",
        "destroy": "leave_management.leave.balance.view",
    }
    
    def has_permission(self, request: Request) -> bool:
        """Check if user has permission."""
        from fusion_auth.permissions import HasPermission
        
        return HasPermission(self.PERMISSIONS.get(request.method.lower(), "view")).has_permission(request)
    
    def has_object_permission(self, request: Request, view, obj) -> bool:
        """Check if user has permission on specific object."""
        # Check if user owns the object
        if obj.user_id != request.user.id:
            return False
        
        return self.has_permission(request)


class LeavePolicyPermission(permissions.BasePermission):
    """Permission class for leave policy operations."""
    
    PERMISSIONS = {
        "view": "leave_management.leave.policy.view",
        "create": "leave_management.leave.policy.manage",
        "update": "leave_management.leave.policy.manage",
        "destroy": "leave_management.leave.policy.manage",
    }
    
    def has_permission(self, request: Request) -> bool:
        """Check if user has permission."""
        from fusion_auth.permissions import HasPermission
        
        return HasPermission(self.PERMISSIONS.get(request.method.lower(), "view")).has_permission(request)
    
    def has_object_permission(self, request: Request, view, obj) -> bool:
        """Check if user has permission on specific object."""
        return self.has_permission(request)


class LeaveSanctionPermission(permissions.BasePermission):
    """Permission class for leave sanction operations."""
    
    PERMISSIONS = {
        "view": "leave_management.leave.sanction.view",
        "create": "leave_management.leave.sanction.view",
        "update": "leave_management.leave.sanction.view",
        "destroy": "leave_management.leave.sanction.view",
    }
    
    def has_permission(self, request: Request) -> bool:
        """Check if user has permission."""
        from fusion_auth.permissions import HasPermission
        
        return HasPermission(self.PERMISSIONS.get(request.method.lower(), "view")).has_permission(request)
    
    def has_object_permission(self, request: Request, view, obj) -> bool:
        """Check if user has permission on specific object."""
        return self.has_permission(request)


# -- Scoped Collection for MODULE/NAV_ITEMS matching placement module pattern --


class ScopedCollection:
    """Scoped collection for MODULE/NAV_ITEMS matching."""
    
    # Define scoped collections for navigation
    SCOPED_COLLECTIONS = {
        "leave_requests": [
            {
                "code": "leave_requests",
                "label": "Leave Requests",
                "icon": "FaCalendar",
                "to": "/leave/requests/",
                "required_permission": "leave_management.leave.view",
            },
        ],
        "my_leave": [
            {
                "code": "my_leave",
                "label": "My Leave Balance",
                "icon": "FaUserClock",
                "to": "/leave/balance/",
                "required_permission": "leave_management.leave.balance.view",
            },
        ],
        "leave_policy": [
            {
                "code": "leave_policy",
                "label": "Leave Policy",
                "icon": "FaFileContract",
                "to": "/leave/policy/",
                "required_permission": "leave_management.leave.policy.view",
            },
        ],
        "holiday_calendar": [
            {
                "code": "holiday_calendar",
                "label": "Holiday Calendar",
                "icon": "FaCalendarAlt",
                "to": "/leave/holiday/",
                "required_permission": "leave_management.leave.holiday.view",
            },
        ],
        "sanctions": [
            {
                "code": "sanctions",
                "label": "Sanctions",
                "icon": "FaGavel",
                "to": "/leave/sanctions/",
                "required_permission": "leave_management.leave.sanction.view",
            },
        ],
    }
    
    def get_scoped_collections(self) -> dict:
        """Get scoped collections filtered by user permissions."""
        from fusion_auth.permissions import HasPermission
        
        permissions = self.get_user_permissions()
        filtered = {}
        
        for name, items in self.SCOPED_COLLECTIONS.items():
            filtered_items = []
            for item in items:
                if item["required_permission"] in permissions:
                    filtered_items.append(item)
            if filtered_items:
                filtered[name] = filtered_items
        
        return filtered
    
    def get_user_permissions(self) -> frozenset:
        """Get user's permissions from request."""
        from fusion_auth.permissions import HasPermission
        
        # In production, this would read from request.principal.permissions
        return frozenset(["leave_management.leave.view"])
