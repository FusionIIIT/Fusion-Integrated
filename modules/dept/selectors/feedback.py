"""Feedback selectors with confidentiality scoping (BR-DEPT-017)."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.dept.models.feedback import Feedback


def list_feedback_for_principal(
    department_code: str,
    principal: Any,
    mine_only: bool = False,
    status: str | None = None,
) -> QuerySet[Feedback]:
    qs = Feedback.objects.filter(department_id=department_code)

    roles = set(getattr(principal, "roles", []))
    is_authorized = bool(roles.intersection({"HOD", "Dept_Admin"})) or getattr(
        principal, "is_staff", False
    )

    if mine_only or not is_authorized:
        user_id = str(getattr(principal, "user_id", getattr(principal, "id", "")))
        qs = qs.filter(submitted_by_id=user_id)

    if status:
        qs = qs.filter(status=status.upper())

    return qs.order_by("-created_at")
