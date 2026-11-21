"""Minimal Department module.

The module is intentionally self-contained until the Department contract is
defined by the owning system.
"""

from .contracts import Department, DepartmentStore

__all__ = ["Department", "DepartmentStore"]
