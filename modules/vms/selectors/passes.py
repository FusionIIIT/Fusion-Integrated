"""Read-only selectors for digital passes."""

from __future__ import annotations

from modules.vms.models import Pass


def get_pass_by_id(pass_id: int) -> Pass | None:
    return (
        Pass.objects.filter(pk=pass_id)
        .select_related("visit_request", "visit_request__visitor")
        .first()
    )


def get_pass_by_number(pass_number: str) -> Pass | None:
    return (
        Pass.objects.filter(pass_number=pass_number)
        .select_related("visit_request", "visit_request__visitor")
        .first()
    )


def get_pass_by_token(qr_token: str) -> Pass | None:
    return (
        Pass.objects.filter(qr_token=qr_token)
        .select_related("visit_request", "visit_request__visitor")
        .first()
    )
