"""Feedback (BR-MMS-020; UC-012/013)."""

from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.mms.models import Feedback
from modules.mms.services import authz


def submit(actor, text: str) -> Feedback:
    if not text or not text.strip():
        raise ConflictError("Feedback text must not be empty.")
    authz.require(actor, "mms.feedback.create")
    with transaction.atomic():
        return Feedback.objects.create(user_id=actor.user_id, text=text.strip())
