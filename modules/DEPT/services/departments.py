"""Small in-memory Department CRUD service.

The repository is a testable seam for the eventual Django persistence layer.
"""

from __future__ import annotations

from dataclasses import replace

from modules.DEPT.domain.validation import (
    DepartmentValidationError,
    normalise_code,
    validate_name,
    validate_parent,
)
from modules.DEPT.models import Department


class DepartmentNotFound(LookupError):
    """Raised when a requested Department id is absent."""


class DepartmentStore:
    """In-memory CRUD store suitable for isolated tests and local prototypes."""

    def __init__(self) -> None:
        self._rows: dict[int, Department] = {}
        self._next_id = 1

    def create(self, *, code: str, name: str, description: str = "",
               parent_id: int | None = None) -> Department:
        code = normalise_code(code)
        name = validate_name(name)
        self._ensure_unique_code(code)
        validate_parent(0, parent_id, self._rows)
        department = Department(
            id=self._next_id, code=code, name=name,
            description=description.strip(), parent_id=parent_id,
        )
        self._rows[department.id] = department
        self._next_id += 1
        return department

    def get(self, department_id: int) -> Department:
        try:
            return self._rows[department_id]
        except KeyError as exc:
            raise DepartmentNotFound(f"Department {department_id} was not found.") from exc

    def list(self, *, active_only: bool = False) -> list[Department]:
        rows = self._rows.values()
        if active_only:
            rows = (row for row in rows if row.is_active)
        return sorted(rows, key=lambda row: (row.name.casefold(), row.id))

    def update(self, department_id: int, *, code: str | None = None,
               name: str | None = None, description: str | None = None,
               parent_id: int | None = None, keep_parent: bool = False) -> Department:
        current = self.get(department_id)
        new_code = normalise_code(code) if code is not None else current.code
        new_name = validate_name(name) if name is not None else current.name
        self._ensure_unique_code(new_code, excluding=department_id)
        new_parent = current.parent_id if keep_parent else parent_id
        validate_parent(department_id, new_parent, self._rows)
        if new_parent is not None and self._is_descendant(new_parent, department_id):
            raise DepartmentValidationError("A department cannot become a child of its descendant.")
        updated = replace(
            current, code=new_code, name=new_name,
            description=current.description if description is None else description.strip(),
            parent_id=new_parent,
        )
        self._rows[department_id] = updated
        return updated

    def deactivate(self, department_id: int) -> Department:
        current = self.get(department_id)
        updated = replace(current, is_active=False)
        self._rows[department_id] = updated
        return updated

    def delete(self, department_id: int) -> None:
        self.get(department_id)
        if any(row.parent_id == department_id for row in self._rows.values()):
            raise DepartmentValidationError("A department with children cannot be deleted.")
        del self._rows[department_id]

    def _ensure_unique_code(self, code: str, excluding: int | None = None) -> None:
        if any(row.code == code and row.id != excluding for row in self._rows.values()):
            raise DepartmentValidationError(f"Department code {code!r} is already in use.")

    def _is_descendant(self, candidate: int, ancestor: int) -> bool:
        seen: set[int] = set()
        current = candidate
        while current not in seen:
            seen.add(current)
            row = self._rows.get(current)
            if row is None or row.parent_id is None:
                return False
            if row.parent_id == ancestor:
                return True
            current = row.parent_id
        return True
