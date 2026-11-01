"""Licensing, rejection appeals, and prior art services (BW-PMS-03..05, UC-PMS-004, 020..023)."""

from __future__ import annotations

import datetime

from django.db import transaction

from modules.pms.domain.constants import (
    ACTOR_APPLICANT,
    ACTOR_DIRECTOR,
    APPEAL_MODIFY,
    APPEAL_OUTCOMES,
    APPEAL_REMAND,
    APPEAL_UPHOLD,
    STATUS_APPEAL_SUBMITTED,
    STATUS_DECISION_MODIFIED,
    STATUS_REJECTED,
    STATUS_REJECTION_UPHELD,
    STATUS_REMANDED_FOR_AMENDMENT,
)
from modules.pms.domain.exceptions import ValidationError
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import (
    AppealDecision,
    LicensingRequest,
    PatentAppeal,
    PatentApplication,
    PriorArtAttachment,
    PriorArtSearchRecord,
)
from modules.pms.services.audit import record_audit_event


@transaction.atomic
def submit_licensing_request(
    application: PatentApplication,
    applicant_user_id: int,
    licensee_name: str,
    licensee_contact: str,
    proposed_terms: str,
    financial_terms: str = "",
) -> LicensingRequest:
    """Submit licensing / technology transfer proposal (UC-PMS-020, BR-PMS-088, 091)."""
    req = LicensingRequest.objects.create(
        application=application,
        user_id=applicant_user_id,
        licensee_name=licensee_name.strip(),
        licensee_contact=licensee_contact.strip(),
        proposed_terms=proposed_terms.strip(),
        financial_terms=financial_terms.strip(),
        status="submitted",
    )

    record_audit_event(
        application=application,
        user_id=applicant_user_id,
        actor_role=ACTOR_APPLICANT,
        action_type="submit_licensing_request",
        details={"licensee_name": licensee_name.strip()},
    )

    return req


@transaction.atomic
def review_licensing_request(
    request: LicensingRequest,
    director_user_id: int,
    decision: str,  # "approved" or "rejected"
    review_notes: str,
) -> LicensingRequest:
    """Director review of licensing proposal (UC-PMS-021)."""
    if decision not in ("approved", "rejected"):
        raise ValidationError(f"Invalid decision {decision!r}. Must be 'approved' or 'rejected'.")

    request.status = decision
    request.review_notes = review_notes.strip()
    request.reviewed_by_director_id = director_user_id
    request.save()

    record_audit_event(
        application=request.application,
        user_id=director_user_id,
        actor_role=ACTOR_DIRECTOR,
        action_type=f"licensing_{decision}",
        details={"review_notes": review_notes.strip()},
    )

    return request


@transaction.atomic
def file_patent_appeal(
    application: PatentApplication,
    applicant_user_id: int,
    grounds: str,
    justification: str,
) -> PatentAppeal:
    """File appeal against rejection (UC-PMS-022, BW-PMS-03, 04, 05, BR-PMS-092..094)."""
    # 1. Only rejected applications eligible (BR-PMS-092)
    if application.status != STATUS_REJECTED:
        raise ValidationError(
            f"Appeal permitted only for 'rejected' applications (current: {application.status!r}).",
            rule_id="BR-PMS-092",
        )

    # 2. Grounds and justification required (BR-PMS-094)
    if not grounds.strip() or not justification.strip():
        raise ValidationError(
            "Appeal requires grounds and detailed justification.",
            rule_id="BR-PMS-094",
        )

    validate_transition(application.status, STATUS_APPEAL_SUBMITTED, ACTOR_APPLICANT)
    prev_status = application.status
    application.status = STATUS_APPEAL_SUBMITTED
    application.save()

    appeal = PatentAppeal.objects.create(
        application=application,
        user_id=applicant_user_id,
        grounds=grounds.strip(),
        justification=justification.strip(),
        status="appeal_submitted",
    )

    record_audit_event(
        application=application,
        user_id=applicant_user_id,
        actor_role=ACTOR_APPLICANT,
        action_type="file_appeal",
        previous_state=prev_status,
        new_state=STATUS_APPEAL_SUBMITTED,
        details={"grounds": grounds.strip()},
    )

    return appeal


@transaction.atomic
def review_patent_appeal(
    appeal: PatentAppeal,
    director_user_id: int,
    outcome: str,  # uphold_rejection, remand_for_amendment, modify_decision
    justification: str,
) -> AppealDecision:
    """Director appeal adjudication (UC-PMS-023, BW-PMS-03, 04, 05, BR-PMS-095)."""
    if outcome not in APPEAL_OUTCOMES:
        raise ValidationError(
            f"Appeal outcome must be one of: {', '.join(sorted(APPEAL_OUTCOMES))}.",
            rule_id="BR-PMS-095",
        )

    application = appeal.application
    prev_status = application.status

    target_status = {
        APPEAL_UPHOLD: STATUS_REJECTION_UPHELD,
        APPEAL_REMAND: STATUS_REMANDED_FOR_AMENDMENT,
        APPEAL_MODIFY: STATUS_DECISION_MODIFIED,
    }[outcome]

    validate_transition(application.status, target_status, ACTOR_DIRECTOR)
    application.status = target_status
    application.save()

    appeal.status = outcome
    appeal.save()

    decision = AppealDecision.objects.create(
        appeal=appeal,
        director_user_id=director_user_id,
        outcome=outcome,
        justification=justification.strip(),
    )

    record_audit_event(
        application=application,
        user_id=director_user_id,
        actor_role=ACTOR_DIRECTOR,
        action_type=f"appeal_{outcome}",
        previous_state=prev_status,
        new_state=target_status,
        details={"justification": justification.strip()},
    )

    return decision


@transaction.atomic
def record_prior_art_search(
    user_id: int,
    query_string: str,
    databases_searched: str,
    results_count: int,
    application: PatentApplication | None = None,
    session_notes: str = "",
) -> PriorArtSearchRecord:
    """Log prior art search query session (UC-PMS-004, BR-PMS-141)."""
    record = PriorArtSearchRecord.objects.create(
        application=application,
        user_id=user_id,
        query_string=query_string.strip(),
        databases_searched=databases_searched.strip(),
        results_count=results_count,
        session_notes=session_notes.strip(),
    )

    record_audit_event(
        application=application,
        user_id=user_id,
        actor_role="researcher",
        action_type="prior_art_search",
        details={"query": query_string.strip(), "results_count": results_count},
    )

    return record


@transaction.atomic
def attach_prior_art_to_application(
    application: PatentApplication,
    user_id: int,
    title: str,
    publication_or_patent_no: str,
    relevance_summary: str,
    authors: str = "",
    publication_date: datetime.date | None = None,
    url_or_doi: str = "",
) -> PriorArtAttachment:
    """Attach prior art reference to an application (UC-PMS-004)."""
    attachment = PriorArtAttachment.objects.create(
        application=application,
        title=title.strip(),
        publication_or_patent_no=publication_or_patent_no.strip(),
        authors_or_inventors=authors.strip(),
        publication_date=publication_date,
        url_or_doi=url_or_doi.strip(),
        relevance_summary=relevance_summary.strip(),
        attached_by_user_id=user_id,
    )

    record_audit_event(
        application=application,
        user_id=user_id,
        actor_role="researcher",
        action_type="attach_prior_art",
        details={"reference": publication_or_patent_no.strip()},
    )

    return attachment
