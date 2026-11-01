"""Yearly Appraisal service (BR-HR-012 to BR-HR-015, BW-HR-04, 05)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hreis.domain.appraisal import (
    AppraisalStatus,
    validate_appraisal_finalization,
    validate_appraisal_submission,
    validate_appraisal_window,
    validate_reviewer_assignment,
)
from modules.hreis.models import AppraisalSubmission, EmployeeServiceRecord
from modules.hreis.services.audit import log_hr_action
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.service_records import get_or_create_service_record
from modules.hreis.services.workflow_config import get_workflow_config


@transaction.atomic
def submit_appraisal(
    *,
    user_id: int,
    username: str,
    academic_year: str,
    content: dict[str, Any],
    is_draft: bool = False,
) -> AppraisalSubmission:
    window_cfg = get_workflow_config("appraisal_window")
    today = date.today()

    try:
        validate_appraisal_window(today, window_cfg)
    except Exception as e:
        raise BadRequestError(str(e)) from e

    appraisal = AppraisalSubmission.objects.select_for_update().filter(
        user_id=user_id, academic_year=academic_year
    ).first()

    status = AppraisalStatus.DRAFT.value if is_draft else AppraisalStatus.SUBMITTED.value
    if appraisal:
        try:
            validate_appraisal_submission(academic_year, content, appraisal.status)
        except Exception as e:
            raise BadRequestError(str(e)) from e

        appraisal.content = content
        appraisal.status = status
        appraisal.save()
    else:
        appraisal = AppraisalSubmission.objects.create(
            user_id=user_id,
            academic_year=academic_year,
            content=content,
            status=status,
        )

    log_hr_action(
        actor_id=user_id,
        actor_username=username,
        actor_role="employee",
        action="submit_appraisal" if not is_draft else "save_appraisal_draft",
        entity_type="appraisal_submission",
        entity_id=appraisal.id,
        details={"academic_year": academic_year, "is_draft": is_draft},
    )

    if not is_draft:
        send_hr_notification(
            user_id=user_id,
            title="Appraisal Submitted",
            message=f"Your annual appraisal for academic year {academic_year} was submitted.",
            category="submission",
            link=f"/hr/appraisals/{appraisal.id}",
        )

    return appraisal


@transaction.atomic
def assign_appraisal_reviewers(
    *,
    appraisal_id: int,
    reviewer_ids: list[int],
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> AppraisalSubmission:
    appraisal = AppraisalSubmission.objects.select_for_update().filter(id=appraisal_id).first()
    if not appraisal:
        raise NotFoundError("Appraisal submission not found.")

    try:
        validate_reviewer_assignment(appraisal.status, reviewer_ids)
    except Exception as e:
        raise BadRequestError(str(e)) from e

    appraisal.assigned_reviewers = reviewer_ids
    if appraisal.status == AppraisalStatus.SUBMITTED.value:
        appraisal.status = AppraisalStatus.UNDER_REVIEW.value
    appraisal.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action="assign_appraisal_reviewers",
        entity_type="appraisal_submission",
        entity_id=appraisal.id,
        details={"reviewers": reviewer_ids},
    )

    for rev_id in reviewer_ids:
        send_hr_notification(
            user_id=rev_id,
            title="Appraisal Review Assigned",
            message=f"You have been assigned to evaluate the appraisal of user {appraisal.user_id} ({appraisal.academic_year}).",
            category="reminder",
            link=f"/hr/appraisals/{appraisal.id}",
        )

    return appraisal


@transaction.atomic
def submit_appraisal_review(
    *,
    appraisal_id: int,
    score: float,
    comments: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> AppraisalSubmission:
    appraisal = AppraisalSubmission.objects.select_for_update().filter(id=appraisal_id).first()
    if not appraisal:
        raise NotFoundError("Appraisal submission not found.")

    if appraisal.is_immutable or appraisal.status == AppraisalStatus.FINALIZED.value:
        raise ConflictError("Appraisal is already finalized and cannot accept reviews.")

    review_entry = {
        "reviewer_id": actor_id,
        "reviewer_username": actor_username,
        "role": actor_role,
        "score": score,
        "comments": comments,
        "timestamp": timezone.now().isoformat(),
    }

    revs = list(appraisal.reviews or [])
    revs.append(review_entry)
    appraisal.reviews = revs
    appraisal.status = AppraisalStatus.UNDER_REVIEW.value
    appraisal.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action="submit_appraisal_review",
        entity_type="appraisal_submission",
        entity_id=appraisal.id,
        details={"score": score},
    )

    return appraisal


@transaction.atomic
def finalize_appraisal(
    *,
    appraisal_id: int,
    final_score: float,
    final_remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> AppraisalSubmission:
    appraisal = AppraisalSubmission.objects.select_for_update().filter(id=appraisal_id).first()
    if not appraisal:
        raise NotFoundError("Appraisal submission not found.")

    try:
        validate_appraisal_finalization(appraisal.status, final_score, final_remarks)
    except Exception as e:
        raise BadRequestError(str(e)) from e

    appraisal.final_score = Decimal(str(final_score))
    appraisal.final_remarks = final_remarks
    appraisal.finalized_at = timezone.now()
    appraisal.status = AppraisalStatus.FINALIZED.value
    appraisal.is_immutable = True  # Permanently immutable (BR-HR-015, AFR-049)
    appraisal.save()

    # Archive in service record (BR-HR-015, AFR-048)
    service_rec = get_or_create_service_record(appraisal.user_id)
    service_rec = EmployeeServiceRecord.objects.select_for_update().get(id=service_rec.id)
    hist = list(service_rec.service_history or [])
    hist.append({
        "event": "Annual Appraisal Finalized",
        "academic_year": appraisal.academic_year,
        "final_score": float(final_score),
        "finalized_by": actor_username,
        "date": str(date.today()),
    })
    service_rec.service_history = hist
    service_rec.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action="finalize_appraisal",
        entity_type="appraisal_submission",
        entity_id=appraisal.id,
        details={"final_score": final_score, "academic_year": appraisal.academic_year},
    )

    send_hr_notification(
        user_id=appraisal.user_id,
        title="Appraisal Finalized",
        message=f"Your appraisal for {appraisal.academic_year} has been finalized with score {final_score}.",
        category="approval",
        link=f"/hr/appraisals/{appraisal.id}",
    )

    return appraisal
