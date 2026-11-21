"""Read selectors for files in Inbox, Outbox, and Drafts."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DRAFT,
)
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement


def get_inbox_files(user_id: int) -> QuerySet[File]:
    """Returns active circulated files held by user, excluding inactive files."""
    return File.objects.filter(
        current_holder_user_id=user_id,
        status=STATE_CIRCULATED,
    ).order_by("-updated_at")


def get_outbox_files(user_id: int) -> QuerySet[File]:
    """Returns circulated or archived files sent by user, excluding drafts."""
    sent_file_ids = (
        FileMovement.objects.filter(from_user_id=user_id)
        .values_list("file_id", flat=True)
        .distinct()
    )
    return File.objects.filter(
        id__in=sent_file_ids,
        status__in=[STATE_CIRCULATED, STATE_ARCHIVED],
    ).order_by("-updated_at")


def get_draft_files(user_id: int) -> QuerySet[File]:
    """Returns draft files owned by user, excluding discarded records."""
    return File.objects.filter(
        owner_user_id=user_id,
        status=STATE_DRAFT,
    ).order_by("-updated_at")
