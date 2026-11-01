"""Yearly Appraisal domain logic (BR-HR-012, BR-HR-013, BR-HR-014, BR-HR-015)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from modules.hreis.domain.exceptions import DomainValidationError


class AppraisalStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    FINALIZED = "finalized"



def validate_appraisal_window(
    current_date: date,
    window_config: dict[str, str | bool] | None,
) -> None:
    """Enforce appraisal submission window (BR-HR-012)."""
    if not window_config or not window_config.get("active", False):
        raise DomainValidationError("Yearly appraisal submission window is currently closed.")

    start_str = window_config.get("start_date")
    end_str = window_config.get("end_date")
    if start_str and end_str:
        start = date.fromisoformat(str(start_str))
        end = date.fromisoformat(str(end_str))
        if current_date < start or current_date > end:
            raise DomainValidationError(
                f"Yearly appraisal can only be submitted between {start} and {end}."
            )


def validate_appraisal_submission(
    academic_year: str,
    content: dict,
    current_status: str,
) -> None:
    if current_status == AppraisalStatus.FINALIZED.value:
        raise DomainValidationError("Finalized appraisals cannot be modified (BR-HR-015).")

    if not academic_year or not academic_year.strip():
        raise DomainValidationError("Academic year is required for appraisal submission.")

    if not content:
        raise DomainValidationError("Appraisal self-assessment content cannot be empty.")


def validate_reviewer_assignment(
    appraisal_status: str,
    reviewer_ids: list[int],
) -> None:
    if appraisal_status == AppraisalStatus.FINALIZED.value:
        raise DomainValidationError("Cannot assign reviewers to a finalized appraisal.")

    if not reviewer_ids:
        raise DomainValidationError("At least one reviewer must be assigned.")


def validate_appraisal_finalization(
    appraisal_status: str,
    final_score: float | None,
    final_remarks: str,
) -> None:
    if appraisal_status == AppraisalStatus.FINALIZED.value:
        raise DomainValidationError("Appraisal is already finalized and immutable (BR-HR-015).")

    if final_score is not None and not (0.0 <= final_score <= 100.0):
        raise DomainValidationError("Appraisal final score must be between 0 and 100.")

    if not final_remarks or not final_remarks.strip():
        raise DomainValidationError("Final remarks must be provided for appraisal finalization.")
