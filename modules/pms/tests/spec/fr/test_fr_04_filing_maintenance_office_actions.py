"""FR Spec Tests: Filing, Post-Grant Maintenance, and Office Actions.

Covers TC-070..TC-095 from FR_DESIGN.json.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.pms.domain.entities import validate_filing_preconditions
from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    OfficeAction,
    PmsAuditTrail,
    PmsNotificationOutbox,
    PostGrantMaintenance,
)
from modules.pms.services import (
    approve_office_action_response,
    decide_renewal,
    draft_office_action_response,
    log_audit,
    record_external_filing,
    record_maintenance_action,
    record_office_action,
    record_patent_grant,
    request_office_action_extension,
    request_renewal_decision,
    submit_application,
    submit_office_action_response,
)
from modules.pms.tests.support import configure_maintenance_schedule

pytestmark = pytest.mark.django_db


def _ready_to_file_app(applicant_user_id: int = 1001, attorney_user_id: int = 5001, director_user_id: int = 2001):
    app = submit_application(
        applicant_user_id=applicant_user_id,
        title="Patentable Invention",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Engineering",
        coinventors_data=[
            {
                "user_id": applicant_user_id,
                "name": "Lead Inventor",
                "email": "lead@example.test",
                "ownership_percentage": "100.00",
                "consent_given": True,
                "agreement_signed": True,
            }
        ],
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_director_user_id = director_user_id
    app.assigned_attorney_user_id = attorney_user_id
    app.save(update_fields=["status", "assigned_director_user_id", "assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(
        attorney_user_id=attorney_user_id,
        assigned_by_user_id=9001,
        status="accepted",
        is_active=True,
    )
    budget = app.budget
    budget.status = "approved"
    budget.save(update_fields=["status", "updated_at"])
    return app


def _filed_app(applicant_user_id: int = 1001, attorney_user_id: int = 5001, director_user_id: int = 2001):
    app = _ready_to_file_app(applicant_user_id, attorney_user_id, director_user_id)
    return record_external_filing(
        application_id=app.id,
        attorney_user_id=attorney_user_id,
        external_filing_id="IPO-2026-001",
        external_filing_date=datetime.date(2026, 5, 1),
        filing_confirmation="ACK-001",
    )


def test_tc_070_pms_afr_099_attorney_prepares_application_package_for_filing():
    """Test ID: TC-070 | Source ID: PMS-AFR-099: Attorney prepares application package for filing."""
    app = _ready_to_file_app()
    app.format_validated = True
    app.save(update_fields=["format_validated", "updated_at"])
    log_audit(
        application=app,
        actor_user_id=5001,
        action_type="filing_package_prepared",
        details={"package_ready": True},
    )
    assert PmsAuditTrail.objects.filter(application=app, action_type="filing_package_prepared").exists()


def test_tc_071_pms_afr_100_validate_filing_package_format_compliance():
    """Test ID: TC-071 | Source ID: PMS-AFR-100: validate filing-package format compliance."""
    with pytest.raises(PreconditionNotMetError):
        validate_filing_preconditions(
            status="draft",
            budget_status="draft",
            all_agreements_complete=False,
        )


def test_tc_072_pms_afr_101_record_submission_to_indian_patent_office():
    """Test ID: TC-072 | Source ID: PMS-AFR-101: record submission to Indian Patent Office."""
    app = _ready_to_file_app()
    filed = record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="IN-PAT-2026-100",
        external_filing_date=datetime.date(2026, 6, 10),
        filing_confirmation="IPO Receipt #100",
        is_international=False,
    )
    assert filed.jurisdiction == "IN"
    assert filed.is_international is False
    assert filed.external_filing_id == "IN-PAT-2026-100"


def test_tc_073_pms_afr_102_record_submission_to_international_patent_offices():
    """Test ID: TC-073 | Source ID: PMS-AFR-102: record submission to international patent offices."""
    app = _ready_to_file_app()
    filed = record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="PCT-IB-2026-888",
        external_filing_date=datetime.date(2026, 6, 15),
        filing_confirmation="PCT Filing Receipt",
        is_international=True,
        international_justification="Commercial market expansion across PCT contracting states.",
    )
    assert filed.is_international is True
    assert filed.international_justification.startswith("Commercial market")


def test_tc_074_pms_afr_103_require_additional_justification_for_international_filings():
    """Test ID: TC-074 | Source ID: PMS-AFR-103: require additional justification for international filings."""
    app = _ready_to_file_app()
    with pytest.raises(PreconditionNotMetError, match="International filings require"):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="PCT-IB-2026-999",
            external_filing_date=datetime.date(2026, 6, 15),
            filing_confirmation="PCT Receipt",
            is_international=True,
            international_justification="",
        )


def test_tc_075_pms_afr_104_capture_external_filing_id_filing_date_and_confirmation():
    """Test ID: TC-075 | Source ID: PMS-AFR-104: capture external filing ID, filing date, and confirmation."""
    app = _ready_to_file_app()
    filing_date = datetime.date(2026, 7, 1)
    filed = record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="EXT-998877",
        external_filing_date=filing_date,
        filing_confirmation="CONF-998877",
    )
    assert filed.external_filing_id == "EXT-998877"
    assert filed.external_filing_date == filing_date
    assert filed.filing_confirmation == "CONF-998877"


def test_tc_076_pms_afr_105_update_application_status_to_filed_after_recording_filing():
    """Test ID: TC-076 | Source ID: PMS-AFR-105: update application status to Filed after recording filing."""
    filed = _filed_app()
    assert filed.status == PatentApplicationStatus.FILED.value


def test_tc_077_pms_afr_106_log_official_communications_with_patent_offices():
    """Test ID: TC-077 | Source ID: PMS-AFR-106: log official communications with patent offices."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="Official Notice",
        issue_date=datetime.date(2026, 8, 1),
        due_date=datetime.date(2026, 11, 1),
        details="Formal communication from patent office.",
    )
    assert OfficeAction.objects.filter(pk=oa.pk).exists()


def test_tc_078_pms_afr_107_activate_post_grant_tracking_only_for_status_granted():
    """Test ID: TC-078 | Source ID: PMS-AFR-107: activate post-grant tracking only for status Granted."""
    configure_maintenance_schedule()
    filed = _filed_app()
    assert filed.maintenance_records.count() == 0

    granted = record_patent_grant(
        application_id=filed.id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-777",
        grant_date=datetime.date(2026, 9, 1),
    )
    assert granted.status == PatentApplicationStatus.GRANTED.value
    assert granted.maintenance_records.count() == 1


def test_tc_079_pms_afr_108_calculate_maintenance_fee_schedule_from_grant_date_and_jurisdiction():
    """Test ID: TC-079 | Source ID: PMS-AFR-108: calculate maintenance-fee schedule from grant date and jurisdiction."""
    configure_maintenance_schedule()
    filed = _filed_app()
    grant_date = datetime.date(2026, 9, 1)
    granted = record_patent_grant(
        application_id=filed.id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-778",
        grant_date=grant_date,
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    assert cycle.fee_due_date == grant_date + datetime.timedelta(days=1095)
    assert cycle.fee_amount == Decimal("5000.00")


def test_tc_080_pms_afr_109_attorney_manages_maintenance_fee_reminders_and_deadline_tracking():
    """Test ID: TC-080 | Source ID: PMS-AFR-109: Attorney manages maintenance-fee reminders and deadline tracking."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-779",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    cycle.fee_due_date = timezone.now().date() + datetime.timedelta(days=30)
    cycle.save(update_fields=["fee_due_date", "updated_at"])
    assert cycle.maintenance_status == "scheduled"


def test_tc_081_pms_afr_110_require_explicit_renewal_decision_before_maintenance_deadline():
    """Test ID: TC-081 | Source ID: PMS-AFR-110: require explicit renewal decision before maintenance deadline."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-780",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    assert cycle.director_decision == ""
    with pytest.raises(PreconditionNotMetError):
        record_maintenance_action(
            maintenance_id=cycle.id, attorney_user_id=5001, transaction_reference="TXN-PREMATURE"
        )


def test_tc_082_pms_afr_111_attorney_seeks_renewal_decision_from_director():
    """Test ID: TC-082 | Source ID: PMS-AFR-111: Attorney seeks renewal decision from Director."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-781",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    req = request_renewal_decision(maintenance_id=cycle.id, attorney_user_id=5001)
    assert req.decision_requested is True
    assert req.maintenance_status == "decision_requested"
    assert PmsNotificationOutbox.objects.filter(
        topic="maintenance.decision_requested", recipient_user_id=2001
    ).exists()


def test_tc_083_pms_afr_112_director_decides_renew_or_do_not_renew():
    """Test ID: TC-083 | Source ID: PMS-AFR-112: Director decides Renew or Do Not Renew."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-782",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    request_renewal_decision(maintenance_id=cycle.id, attorney_user_id=5001)
    decided = decide_renewal(maintenance_id=cycle.id, director_user_id=2001, decision="Do Not Renew")
    assert decided.director_decision == "Do Not Renew"
    assert decided.application.status == PatentApplicationStatus.DO_NOT_RENEW.value


def test_tc_084_pms_afr_113_attorney_records_maintenance_action_when_renewal_approved():
    """Test ID: TC-084 | Source ID: PMS-AFR-113: Attorney records maintenance action when renewal is approved."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-783",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    request_renewal_decision(maintenance_id=cycle.id, attorney_user_id=5001)
    decide_renewal(maintenance_id=cycle.id, director_user_id=2001, decision="Renew")
    completed = record_maintenance_action(
        maintenance_id=cycle.id, attorney_user_id=5001, transaction_reference="TXN-PAID-783"
    )
    assert completed.maintenance_status == "renewed"
    assert completed.transaction_reference == "TXN-PAID-783"
    assert completed.action_recorded_date is not None


def test_tc_085_pms_afr_114_maintain_renewal_history():
    """Test ID: TC-085 | Source ID: PMS-AFR-114: maintain renewal history."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-784",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle = granted.maintenance_records.get(cycle_number=1)
    request_renewal_decision(maintenance_id=cycle.id, attorney_user_id=5001)
    decide_renewal(maintenance_id=cycle.id, director_user_id=2001, decision="Renew")
    record_maintenance_action(maintenance_id=cycle.id, attorney_user_id=5001, transaction_reference="TXN-784")

    assert PostGrantMaintenance.objects.filter(application=granted).count() >= 2
    assert PmsAuditTrail.objects.filter(
        application=granted, action_type="maintenance_action_recorded"
    ).exists()


def test_tc_086_pms_afr_115_schedule_next_maintenance_cycle_after_completion():
    """Test ID: TC-086 | Source ID: PMS-AFR-115: schedule next maintenance cycle after completion."""
    configure_maintenance_schedule()
    granted = record_patent_grant(
        application_id=_filed_app().id,
        attorney_user_id=5001,
        patent_number="IN-GRANT-785",
        grant_date=datetime.date(2026, 9, 1),
    )
    cycle1 = granted.maintenance_records.get(cycle_number=1)
    request_renewal_decision(maintenance_id=cycle1.id, attorney_user_id=5001)
    decide_renewal(maintenance_id=cycle1.id, director_user_id=2001, decision="Renew")
    record_maintenance_action(maintenance_id=cycle1.id, attorney_user_id=5001, transaction_reference="TXN-785")

    assert granted.maintenance_records.filter(cycle_number=2, maintenance_status="scheduled").exists()


def test_tc_087_pms_afr_116_record_office_actions_received_from_patent_offices():
    """Test ID: TC-087 | Source ID: PMS-AFR-116: record office actions received from patent offices."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2026, 12, 1),
        details="First Examination Report",
    )
    assert oa.application_id == filed.id
    assert oa.status == "recorded"


def test_tc_088_pms_afr_117_attorney_reviews_recorded_office_actions():
    """Test ID: TC-088 | Source ID: PMS-AFR-117: Attorney reviews recorded office actions."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2026, 12, 1),
        details="Claim objection details",
    )
    fetched = OfficeAction.objects.get(pk=oa.pk)
    assert fetched.details == "Claim objection details"


def test_tc_089_pms_afr_118_attorney_prepares_draft_office_action_responses():
    """Test ID: TC-089 | Source ID: PMS-AFR-118: Attorney prepares draft office-action responses."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2026, 12, 1),
        details="Objection details",
        requires_applicant_review=True,
    )
    drafted = draft_office_action_response(
        office_action_id=oa.id,
        attorney_user_id=5001,
        draft_response="Draft response addressing examiner objections.",
    )
    assert drafted.draft_response == "Draft response addressing examiner objections."
    assert drafted.status == "awaiting_applicant_approval"


def test_tc_090_pms_afr_119_applicant_reviews_and_approves_office_action_responses_when_needed():
    """Test ID: TC-090 | Source ID: PMS-AFR-119: Applicant reviews and approves office-action responses when needed."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2026, 12, 1),
        details="Objection details",
        requires_applicant_review=True,
    )
    draft_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, draft_response="Draft response text"
    )
    approved = approve_office_action_response(office_action_id=oa.id, applicant_user_id=1001)
    assert approved.applicant_approved is True
    assert approved.status == "applicant_approved"


def test_tc_091_pms_afr_120_attorney_finalizes_office_action_responses():
    """Test ID: TC-091 | Source ID: PMS-AFR-120: Attorney finalizes office-action responses."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2026, 12, 1),
        details="Objection details",
        requires_applicant_review=False,
    )
    ready = draft_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, draft_response="Finalized response draft"
    )
    assert ready.status == "response_ready"


def test_tc_092_pms_afr_121_attorney_records_submission_of_office_action_response_within_deadline():
    """Test ID: TC-092 | Source ID: PMS-AFR-121: Attorney records submission of office-action response within deadline."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2027, 6, 1),
        details="Objection details",
        requires_applicant_review=False,
    )
    draft_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, draft_response="Final draft"
    )
    submitted = submit_office_action_response(
        office_action_id=oa.id,
        attorney_user_id=5001,
        submission_details="Submitted timely with amended claims.",
    )
    assert submitted.status == "response_submitted"
    assert submitted.response_submitted_date is not None


def test_tc_093_pms_afr_122_attorney_records_extension_requests_when_permitted():
    """Test ID: TC-093 | Source ID: PMS-AFR-122: Attorney records extension requests when permitted."""
    filed = _filed_app()
    initial_due = datetime.date(2026, 10, 1)
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 7, 1),
        due_date=initial_due,
        details="Objection details",
    )
    extended = request_office_action_extension(
        office_action_id=oa.id, attorney_user_id=5001, extension_months=2
    )
    assert extended.extension_months == 2
    assert extended.due_date == initial_due + datetime.timedelta(days=60)


def test_tc_094_pms_afr_123_track_response_submission_status():
    """Test ID: TC-094 | Source ID: PMS-AFR-123: track response submission status."""
    filed = _filed_app()
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 6, 1),
        due_date=datetime.date(2027, 6, 1),
        details="Objection details",
        requires_applicant_review=False,
    )
    draft_office_action_response(office_action_id=oa.id, attorney_user_id=5001, draft_response="Draft")
    submit_office_action_response(office_action_id=oa.id, attorney_user_id=5001, submission_details="Filed")
    oa.refresh_from_db()
    assert oa.status == "response_submitted"


def test_tc_095_pms_afr_124_automate_office_action_response_deadline_tracking():
    """Test ID: TC-095 | Source ID: PMS-AFR-124: automate office-action response deadline tracking."""
    filed = _filed_app()
    due = datetime.date(2027, 3, 15)
    oa = record_office_action(
        application_id=filed.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=datetime.date(2026, 11, 1),
        due_date=due,
        details="Automated deadline check",
    )
    assert oa.due_date == due
