"""State machine and workflow transitions for Leave Management (ELM).

Pure Python — no Django or HTTP dependencies.
"""
from modules.elm.domain.errors import IllegalStateTransitionError


class ElmStateMachine:
    """State transition logic for ELM requests."""

    @staticmethod
    def transition_unit_head(
        category_code: str,
        current_status: str,
        action: str,  # "approve", "reject", "recommend", "not_recommend"
    ) -> tuple[str, str]:
        """Process Unit Head review transition.

        Returns (new_status, recommendation_value).
        """
        if current_status != "submitted":
            raise IllegalStateTransitionError(
                f"Cannot perform Unit Head review on request in status '{current_status}'."
            )

        if category_code in ("CL", "RH"):
            # Unit Head has final sanction authority for CL and RH
            if action == "approve":
                return "approved", "recommended"
            if action == "reject":
                return "rejected", "not_recommended"
            raise IllegalStateTransitionError(
                f"Action '{action}' is invalid for CL/RH. Must be 'approve' or 'reject'."
            )

        # For SCL, EL, COL, VL: Unit Head recommends or not recommends, then routes to sanctioner
        if action in ("recommend", "approve"):
            return "pending_sanction", "recommended"
        if action in ("not_recommend", "reject"):
            return "pending_sanction", "not_recommended"

        raise IllegalStateTransitionError(
            f"Action '{action}' is invalid for Unit Head review of {category_code}."
        )

    @staticmethod
    def transition_sanctioning_authority(
        category_code: str,
        current_status: str,
        action: str,  # "approve", "reject"
    ) -> str:
        """Process Sanctioning Authority final decision for higher-sanction leave."""
        if current_status != "pending_sanction":
            raise IllegalStateTransitionError(
                f"Cannot sanction request in '{current_status}'. Expected 'pending_sanction'."
            )

        if action == "approve":
            return "approved"
        if action == "reject":
            return "rejected"

        raise IllegalStateTransitionError(
            f"Action '{action}' is invalid. Must be 'approve' or 'reject'."
        )

    @staticmethod
    def transition_substitute(
        current_status: str,
        action: str,  # "accept", "decline"
    ) -> tuple[str, str]:
        """Process Substitute consent response.

        Returns (new_status, substitute_status).
        """
        if current_status != "pending_substitute":
            raise IllegalStateTransitionError(
                f"Cannot record substitute response for request in status '{current_status}'."
            )

        if action == "accept":
            return "submitted", "accepted"
        if action == "decline":
            return "pending_substitute", "declined"

        raise IllegalStateTransitionError(
            f"Action '{action}' is invalid for substitute response. Must be 'accept' or 'decline'."
        )

    @staticmethod
    def transition_withdraw(current_status: str) -> str:
        """Process applicant withdrawal before final approval."""
        terminal_statuses = {"approved", "rejected", "withdrawn", "cancelled"}
        if current_status in terminal_statuses:
            raise IllegalStateTransitionError(
                f"Cannot withdraw leave request in final status '{current_status}'."
            )
        return "withdrawn"
