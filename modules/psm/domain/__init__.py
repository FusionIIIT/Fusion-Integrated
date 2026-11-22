"""
Pure Python Domain Layer for PSM (Purchase and Stores Management).
Strictly NO Django imports in this package.
"""

from .indent_state import (
    IndentState,
    can_transition,
    is_modifiable,
    TRANSITION_MATRIX,
)
from .rules import (
    validate_indent_completeness,
    is_possible_duplicate,
    determine_procurement_routing,
    determine_procurement_method,
    validate_rejection_justification,
)
from .three_way_match import perform_three_way_match

__all__ = [
    "IndentState",
    "can_transition",
    "is_modifiable",
    "TRANSITION_MATRIX",
    "validate_indent_completeness",
    "is_possible_duplicate",
    "determine_procurement_routing",
    "determine_procurement_method",
    "validate_rejection_justification",
    "perform_three_way_match",
]
