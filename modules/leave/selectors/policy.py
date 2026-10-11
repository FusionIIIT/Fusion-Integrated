"""Policy selectors.

Implements queries for current configured policy (BR-EL-030).
"""
from modules.leave.models.policy import LeavePolicy


def get_current_policy() -> LeavePolicy:
    """Returns the current configured leave policy, creating default if absent."""
    policy = LeavePolicy.objects.first()
    if not policy:
        policy = LeavePolicy.objects.create()
    return policy
