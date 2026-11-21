"""The public surface other modules may use."""

from modules.DEPT.models import Department
from modules.DEPT.services.departments import DepartmentStore

__all__ = ["Department", "DepartmentStore"]

# TODO(specification gap): add employee/unit-head and IAM integration when a
# Department-specific specification is supplied. The available documents are
# ELM requirements and do not define ownership or Department CRUD APIs.
