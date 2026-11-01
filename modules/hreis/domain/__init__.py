"""Pure-Python domain logic for HR-EIS module.

Must NOT import Django, DRF, Celery, or external frameworks.
"""
from modules.hreis.domain.exceptions import DomainValidationError

__all__ = ["DomainValidationError"]
