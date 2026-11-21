"""Public interface functions exposed by the File Tracking System (FTS) module.

This module serves as the contract for other platform modules to query and interact
with FTS data without coupling to internal models or database tables.
All query functions strictly accept and return plural sequences per platform guidelines.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from modules.fts.models import FTSFile
from modules.fts.selectors.inbox_outbox import get_user_inbox_files


@dataclass(frozen=True)
class FileSummaryDTO:
    """Public read-only DTO representing an institutional file."""

    file_id: int
    uin: str
    subject: str
    priority: str
    category: str
    status: str
    creator_id: str
    current_holder_id: str


def get_files_by_uins(uins: Sequence[str]) -> list[FileSummaryDTO]:
    """Retrieves file summaries for a sequence of unique identification numbers (UINs).

    :param uins: Sequence of UIN strings (e.g. ['FTS-2024-0001']).
    :return: List of FileSummaryDTO objects.
    """
    if not uins:
        return []

    files = FTSFile.objects.filter(uin__in=uins)
    return [
        FileSummaryDTO(
            file_id=f.id,
            uin=f.uin,
            subject=f.subject,
            priority=f.priority,
            category=f.category,
            status=f.status,
            creator_id=f.creator_id,
            current_holder_id=f.current_holder_id,
        )
        for f in files
    ]


def get_active_inbox_files_for_employees(
    employee_ids: Sequence[str],
) -> dict[str, list[FileSummaryDTO]]:
    """Retrieves active inbox files currently held by the given sequence of employees.

    :param employee_ids: Sequence of employee user IDs.
    :return: Mapping of employee_id -> list of FileSummaryDTO.
    """
    result: dict[str, list[FileSummaryDTO]] = {}
    for emp_id in employee_ids:
        inbox_items = get_user_inbox_files(user_id=emp_id)
        result[emp_id] = [
            FileSummaryDTO(
                file_id=item["id"],
                uin=item["uin"],
                subject=item["subject"],
                priority=item["priority"],
                category=item["category"],
                status=item["status"],
                creator_id=item["creator_id"],
                current_holder_id=item["current_holder_id"],
            )
            for item in inbox_items
        ]
    return result

