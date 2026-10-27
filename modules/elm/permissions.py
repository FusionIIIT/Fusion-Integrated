# ELM Permissions: Defines the authorization checks required for each action.

from enum import Enum

class ELMAction(Enum):
    """Defines atomic actions within the ELM module."""
    SUBMIT_APPLICATION = "elm:apply:submit"
    VIEW_OWN_BALANCE = "elm:view:balance:self"
    REVIEW_LEAVE = "elm:review:decision"
    CONFIGURE_WORKFLOW = "elm:config:workflow"
    RECORD_OFFLINE_LEAVE = "elm:admin:sync"

class RolePermissionMapper:
    """Maps system roles (from fusion_auth) to ELM capabilities."""

    @staticmethod
    def check_role(required_action: ELMAction, user_roles: set[str]) -> bool:
        """
        Checks if a user's roles grant them permission for a specific ELM action.
        This maps directly to BR-EL-036 (Role-based authorization).
        """
        # Example mapping:
        if required_action == ELMAction.SUBMIT_APPLICATION:
            # Only Faculty or Staff (ACT-01) can submit.
            return any(role in user_roles for role in ["ACT-01_Faculty", "ACT-01_Staff"])
        
        if required_action == ELMAction.REVIEW_LEAVE:
            # Requires Unit Head (ACT-03) or higher.
            return any(role in user_roles for role in ["ACT-03_UnitHead", "ACT-05_Dean", "ACT-06_Registrar", "ACT-07_Director"])
        
        # ... other mappings based on Appendix A and B
        return False
