"""
Indent Read Selectors.
"""

from typing import Any, Optional
from django.db.models import QuerySet
from modules.psm.models import Indent, IndentVersion
from .scoping import get_visible_indents_for_user


def list_indents(principal: Any, status: Optional[str] = None) -> QuerySet[Indent]:
    """List all scoped indents visible to the principal, optionally filtered by status."""
    qs = get_visible_indents_for_user(principal)
    if status:
        qs = qs.filter(status=str(status).strip().upper())
    return qs


def get_indent_by_id(principal: Any, indent_id: Any) -> Optional[Indent]:
    """Retrieve a single indent if visible to the principal; otherwise returns None."""
    qs = get_visible_indents_for_user(principal)
    try:
        # Support both primary key (int) and business indent_id (str)
        if isinstance(indent_id, int) or (isinstance(indent_id, str) and indent_id.isdigit()):
            return qs.filter(id=int(indent_id)).first()
        return qs.filter(indent_id=str(indent_id)).first()
    except Exception:
        return None


def get_indent_version_history(principal: Any, indent_id: Any) -> Optional[QuerySet[IndentVersion]]:
    """Retrieve version history for an indent visible to the principal."""
    indent = get_indent_by_id(principal, indent_id)
    if indent is None:
        return None
    return indent.versions.all().order_by("-version_number")
