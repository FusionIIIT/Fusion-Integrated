"""External patent filing record service (BW-PMS-11, BR-PMS-020, 055, 056, 128)."""

from __future__ import annotations

import datetime

from django.db import transaction

from modules.pms.domain.constants import ACTOR_ATTORNEY, STATUS_FILED
from modules.pms.domain.exceptions import ValidationError
from modules.pms.domain.rules import check_pre_filing_prerequisites
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import ExternalFilingRecord, PatentApplication
from modules.pms.services.audit import record_audit_event


@transaction.atomic
def record_external_patent_filing(
    application: PatentApplication,
    attorney_user_id: int,
    jurisdiction: str,
    filing_number: str,
    filing_date: datetime.date,
    patent_office: str,
    confirmation_details: str,
    international_justification: str = "",
) -> ExternalFilingRecord:
    """Record external patent filing once prerequisites are complete (UC-PMS-013, BW-PMS-11)."""
    # 1. Check pre-filing prerequisites
    has_agreements = (
        application.agreements.filter(status="completed").exists()
        or not application.agreements.filter(status__in=["draft", "circulated"]).exists()
    )
    has_budget_approved = hasattr(application, "budget") and application.budget.status == "approved"
    has_assessment = application.patentability_assessments.exists()

    check_pre_filing_prerequisites(
        budget_approved=has_budget_approved,
        inventor_agreements_completed=has_agreements,
        patentability_assessed=has_assessment,
    )

    # 2. International filing requires justification (Problem Statement 2.3.8)
    if jurisdiction.upper() != "IN" and not international_justification.strip():
        raise ValidationError(
            "International patent filings require recorded justification.",
            rule_id="BR-PMS-056",
        )

    # 3. State transition: Pre-filing -> Filed
    validate_transition(application.status, STATUS_FILED, ACTOR_ATTORNEY)

    prev_status = application.status
    application.status = STATUS_FILED
    application.save()

    # 4. Create ExternalFilingRecord
    record = ExternalFilingRecord.objects.create(
        application=application,
        jurisdiction=jurisdiction.upper().strip(),
        filing_number=filing_number.strip(),
        filing_date=filing_date,
        patent_office=patent_office.strip(),
        confirmation_details=confirmation_details.strip(),
        international_justification=international_justification.strip(),
        recorded_by_user_id=attorney_user_id,
    )

    # 5. Audit log
    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="record_external_filing",
        previous_state=prev_status,
        new_state=STATUS_FILED,
        details={
            "filing_number": record.filing_number,
            "jurisdiction": record.jurisdiction,
            "patent_office": record.patent_office,
        },
    )

    return record
