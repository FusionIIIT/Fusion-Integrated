"""Validation rules for Department records."""

from __future__ import annotations

import re
from collections.abc import Collection


class DepartmentValidationError(ValueError):
    """Raised when a Department violates a module rule."""


_CODE = re.compile(r"^[A-Z][A-Z0-9_-]{1,31}$")


def normalise_code(code: str) -> str:
    value = (code or "").strip().upper()
    if not _CODE.fullmatch(value):
        raise DepartmentValidationError(
            "Department code must be 2-32 characters and contain only A-Z, 0-9, '_' or '-'."
        )
    return value


def validate_name(name: str) -> str:
    value = " ".join((name or "").split())
    if not value:
        raise DepartmentValidationError("Department name is required.")
    if len(value) > 120:
        raise DepartmentValidationError("Department name must be at most 120 characters.")
    return value


def validate_parent(department_id: int, parent_id: int | None,
                    existing_ids: Collection[int]) -> None:
    if parent_id is None:
        return
    if parent_id == department_id:
        raise DepartmentValidationError("A department cannot be its own parent.")
    if parent_id not in existing_ids:
        raise DepartmentValidationError("Parent department does not exist.")
