"""Approval authority determination (BR-EL-016..020)."""
from __future__ import annotations

from modules.leave.domain.categories import CL, RH


def is_unit_head_final(category: str) -> bool:
    """BR-EL-016: For CL and RH, Unit Head is the final sanctioning authority."""
    return category in (CL, RH)


def can_self_sanction(user_role: str) -> bool:
    """BR-EL-020: Director-specific self-sanction rule."""
    return user_role.lower() == "director"
