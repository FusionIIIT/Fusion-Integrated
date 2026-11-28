"""Input checks and refusal wording shared by the module's services."""
from __future__ import annotations

from core.api.exceptions import DomainError

NOT_LED = "No such club among the clubs you lead. Choose one of your clubs from My Clubs."


def required_text(value: str, field: str, message: str, detail: str = "") -> str:
    """The stripped text, or a refusal naming the empty field."""
    text = (value or "").strip()
    if not text:
        raise DomainError(message, code="missing_field",
                          details=[{"field": field, "message": detail or message}])
    return text
