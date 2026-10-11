"""
Assignment 6: ELM Implementation for Fusion ERP Base System
Generated for: Roll No. 23bcs151
"""

class RoleAssignmentManager:
    """
    Handles role assignments and permission verification for Fusion ERP modules.
    """
    def __init__(self, user_id: str, role_name: str):
        self.user_id = user_id
        self.role_name = role_name
        self.assigned_permissions = []

    def assign_role(self) -> dict:
        """
        Assigns the specified role and initializes base module permissions.
        """
        if not self.user_id or not self.role_name:
            return {
                "status": "FAILED",
                "error": "User ID or Role Name cannot be empty."
            }

        # Base role mapping for Fusion ERP modules
        role_permissions_map = {
            "Student": ["view_courses", "submit_assignments", "view_grades"],
            "Faculty": ["grade_assignments", "manage_courses", "assign_roles"],
            "Admin": ["full_access", "manage_system_roles", "manage_users"]
        }

        self.assigned_permissions = role_permissions_map.get(
            self.role_name, ["view_dashboard"]
        )

        return {
            "status": "SUCCESS",
            "user_id": self.user_id,
            "role": self.role_name,
            "permissions": self.assigned_permissions
        }

    def verify_permission(self, permission: str) -> bool:
        """
        Checks if the assigned user has a specific permission.
        """
        return permission in self.assigned_permissions


if __name__ == "__main__":
    # Test execution for verification
    test_user = "23bcs151"
    test_role = "Student"

    manager = RoleAssignmentManager(user_id=test_user, role_name=test_role)
    result = manager.assign_role()
    
    print("--- Role Assignment Result ---")
    print(f"Status: {result['status']}")
    print(f"User: {result['user_id']}")
    print(f"Assigned Role: {result['role']}")
    print(f"Permissions: {', '.join(result['permissions'])}")
