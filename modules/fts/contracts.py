"""FTS public contracts surface for cross-module integration (CFR-FTS-012, BR-FTS-014)."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.fts.models import FTSFile


@dataclass(frozen=True)
class FileSummaryDTO:
    id: int
    file_id: str
    subject: str
    status: str
    creator_id: int
    owner_id: int
    current_holder_id: int | None
    movement_count: int


def get_file_summaries(file_ids: Sequence[int]) -> dict[int, FileSummaryDTO]:
    """Return status and holder summaries for the specified file primary keys."""
    ids = {int(i) for i in file_ids if i is not None}
    if not ids:
        return {}
    files = FTSFile.objects.filter(id__in=ids).prefetch_related("movements")
    return {
        f.id: FileSummaryDTO(
            id=f.id,
            file_id=f.file_id,
            subject=f.subject,
            status=f.status,
            creator_id=f.creator_id,
            owner_id=f.owner_id,
            current_holder_id=f.current_holder_id,
            movement_count=f.movements.count(),
        )
        for f in files
    }


def get_file_summaries_by_code(file_codes: Sequence[str]) -> dict[str, FileSummaryDTO]:
    """Return status and holder summaries for the specified business file_id strings."""
    codes = {str(c) for c in file_codes if c}
    if not codes:
        return {}
    files = FTSFile.objects.filter(file_id__in=codes).prefetch_related("movements")
    return {
        f.file_id: FileSummaryDTO(
            id=f.id,
            file_id=f.file_id,
            subject=f.subject,
            status=f.status,
            creator_id=f.creator_id,
            owner_id=f.owner_id,
            current_holder_id=f.current_holder_id,
            movement_count=f.movements.count(),
        )
        for f in files
    }
