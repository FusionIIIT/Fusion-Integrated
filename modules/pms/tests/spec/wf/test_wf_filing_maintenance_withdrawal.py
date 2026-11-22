
"""Workflow (WF) tests for external filing, office actions, maintenance, and withdrawal.

Covers:
- WF-TC-014 (BW-PMS-11: Step 1 (External Filing Path))
- WF-TC-015 (BW-PMS-12: Step 1-4 (Office-Action Response with Applicant Review))
- WF-TC-016 (BW-PMS-13: Step 1-3 (Office-Action Response without Applicant Review))
- WF-TC-017 (BW-PMS-14: Step 1-3 (Maintenance Renewal Path))
- WF-TC-018 (BW-PMS-15: Step 1-2 (Maintenance Non-Renewal Path))
- WF-TC-019 (BW-PMS-16: Step 1 (Generic Pre-Filing Withdrawal Transition))
- WF-TC-020 (BW-PMS-16: Step 1 Guard (Withdrawal Eligibility / Reason / Consent Missing))
- WF-TC-022 (CW-PMS-05: Step 1-7 (Candidate Pre-Filing States Withdrawal Coverage))
"""

from datetime import date
from decimal import Decimal

import pytest

from modules.pms.domain.errors import WithdrawalNotAllowedError
from modules.pms.domain.state_machine import (
    WITHDRAWAL_ELIGIBLE_STATES,
    PatentApplicationStatus,
)
from modules.pms.models import AttorneyPanel
from modules.pms.services import (
    approve_office_action_response,
    assign_attorney,
    assign_director,
    decide_budget,
    decide_renewal,
    draft_office_action_response,
    record_external_filing,
    record_maintenance_action,
    record_office_action,
    record_patent_grant,
    record_withdrawal_consent,
    request_renewal_decision,
    respond_to_attorney_assignment,
    submit_application,
    submit_director_review,
    submit_office_action_response,
    submit_or_update_budget,
    withdraw_application,
)
from modules.pms.tests.support import configure_maintenance_schedule

pytestmark = pytest.mark.django_db


def test_wf_tc_014_bw_pms_11_step_1_external_filing_path():
    """WF-TC-014 | BW-PMS-11: Step 1 (External Filing Path).

    Verify external filing is recorded when all pre-filing preconditions are
    satisfied.
    """
    AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Filing Attorney",
        email="filing@example.test",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    app = submit_application(
        applicant_user_id=1001,
        title="Solid-State Battery Cell",
        abstract="High-energy solid-state electrolyte cell.",
        detailed_description="Full cell architecture and manufacturing steps.",
        claims="1. A solid-state battery cell...",
        domain="Energy",
        coinventors_data=[
            {
                "user_id": 1001,
                "name": "Lead Inventor",
                "email": "lead@example.test",
                "ownership_percentage": "100.00",
                "agreement_signed": True,
                "consent_given": True,
            }
        ],
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification=(
            "Technical merits and claims are approved for patent filing."
        ),
    )
    assignment = assign_attorney(
        application_id=app.id,
        attorney_user_id=5001,
        assigned_by_user_id=9001,
    )
    respond_to_attorney_assignment(
        assignment_id=assignment.id,
        attorney_user_id=5001,
        accept=True,
    )
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("20000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=3001,
    )
    decide_budget(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Approved within budget.",
    )

    filed_app = record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="EXT-2026-0042",
        external_filing_date=date(2026, 11, 10),
        filing_confirmation="Confirmed receipt by patent office.",
    )
    filed_app.refresh_from_db()
    assert filed_app.status == PatentApplicationStatus.FILED.value
    assert filed_app.external_filing_id == "EXT-2026-0042"


def test_wf_tc_015_bw_pms_12_step_1_4_office_action_with_applicant_review():
    """WF-TC-015 | BW-PMS-12: Step 1-4 (Office-Action Response with Applicant Review).

    Verify recording an office action, obtaining Applicant approval, and
    submitting the response within deadline/extension.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Adaptive Antenna Array",
        abstract="Beamforming antenna array.",
        detailed_description="Detailed antenna array design.",
        claims="1. An antenna array...",
        domain="Communications",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])

    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="Examination Report",
        issue_date=date(2026, 11, 1),
        due_date=date(2027, 2, 1),
        details="Office action requiring response.",
        requires_applicant_review=True,
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.OFFICE_ACTION_RECORDED.value

    draft_office_action_response(
        office_action_id=oa.id,
        attorney_user_id=5001,
        draft_response="Drafted response addressing office action items.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL.value

    approve_office_action_response(
        office_action_id=oa.id,
        applicant_user_id=1001,
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPLICANT_APPROVED.value

    submit_office_action_response(
        office_action_id=oa.id,
        attorney_user_id=5001,
        submission_details="Submitted finalized office action response.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESPONSE_SUBMITTED.value


def test_wf_tc_016_bw_pms_13_step_1_3_office_action_without_applicant_review():
    """WF-TC-016 | BW-PMS-13: Step 1-3 (Office-Action Response without Applicant Review).

    Verify recording an office action and submitting the response without
    Applicant review when not required.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Formalities Correction Filing",
        abstract="Formalities correction for filed application.",
        detailed_description="Detailed formalities response.",
        claims="1. A system...",
        domain="Engineering",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])

    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="Formalities Notice",
        issue_date=date(2026, 11, 1),
        due_date=date(2026, 12, 15),
        details="Formalities notice not requiring applicant approval.",
        requires_applicant_review=False,
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.OFFICE_ACTION_RECORDED.value

    draft_office_action_response(
        office_action_id=oa.id,
        attorney_user_id=5001,
        draft_response="Prepared formalities response.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESPONSE_READY.value

    submit_office_action_response(
        office_action_id=oa.id,
        attorney_user_id=5001,
        submission_details="Submitted formalities response.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESPONSE_SUBMITTED.value


def test_wf_tc_017_bw_pms_14_step_1_3_maintenance_renewal_path():
    """WF-TC-017 | BW-PMS-14: Step 1-3 (Maintenance Renewal Path).

    Verify a maintenance renewal request is approved by the Director and
    recorded by the Attorney with next cycle scheduled.
    """
    configure_maintenance_schedule()
    app = submit_application(
        applicant_user_id=1001,
        title="Granted Sensor Patent",
        abstract="Granted sensor apparatus.",
        detailed_description="Detailed sensor design.",
        claims="1. A sensor apparatus...",
        domain="Sensors",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.assigned_director_user_id = 3001
    app.save(
        update_fields=[
            "status",
            "assigned_attorney_user_id",
            "assigned_director_user_id",
            "updated_at",
        ]
    )

    record_patent_grant(
        application_id=app.id,
        attorney_user_id=5001,
        patent_number="PAT-77701",
        grant_date=date(2026, 11, 1),
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.GRANTED.value

    maint = app.maintenance_records.first()
    assert maint is not None

    request_renewal_decision(maintenance_id=maint.id, attorney_user_id=5001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWAL_DECISION_REQUESTED.value

    decide_renewal(maintenance_id=maint.id, director_user_id=3001, decision="Renew")
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWAL_APPROVED.value

    record_maintenance_action(
        maintenance_id=maint.id,
        attorney_user_id=5001,
        transaction_reference="RENEW-TXN-001",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWED.value
    assert app.maintenance_records.count() == 2


def test_wf_tc_018_bw_pms_15_step_1_2_maintenance_non_renewal_path():
    """WF-TC-018 | BW-PMS-15: Step 1-2 (Maintenance Non-Renewal Path).

    Verify a maintenance decision due can result in a Do Not Renew decision by
    the Director.
    """
    configure_maintenance_schedule()
    app = submit_application(
        applicant_user_id=1001,
        title="Non-Renewed Patent",
        abstract="Patent scheduled for non-renewal.",
        detailed_description="Detailed specification.",
        claims="1. A device...",
        domain="Sensors",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.assigned_director_user_id = 3001
    app.save(
        update_fields=[
            "status",
            "assigned_attorney_user_id",
            "assigned_director_user_id",
            "updated_at",
        ]
    )

    record_patent_grant(
        application_id=app.id,
        attorney_user_id=5001,
        patent_number="PAT-77702",
        grant_date=date(2026, 11, 1),
    )
    maint = app.maintenance_records.first()
    assert maint is not None

    request_renewal_decision(maintenance_id=maint.id, attorney_user_id=5001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWAL_DECISION_REQUESTED.value

    decide_renewal(
        maintenance_id=maint.id,
        director_user_id=3001,
        decision="Do Not Renew",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.DO_NOT_RENEW.value


def test_wf_tc_019_bw_pms_16_step_1_generic_pre_filing_withdrawal_transition():
    """WF-TC-019 | BW-PMS-16: Step 1 (Generic Pre-Filing Withdrawal Transition).

    Verify pre-filing withdrawal succeeds when application is in a configured
    withdrawal-eligible pre-filing state with reason and required consent.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Withdrawable Application",
        abstract="Application with co-inventor consent.",
        detailed_description="Detailed description.",
        claims="1. A method...",
        domain="Software",
        coinventors_data=[
            {
                "user_id": 1001,
                "name": "Lead Inventor",
                "email": "lead@example.test",
                "ownership_percentage": "50.00",
                "agreement_signed": True,
                "consent_given": True,
            },
            {
                "user_id": 2001,
                "name": "Co-Inventor",
                "email": "coinv@example.test",
                "ownership_percentage": "50.00",
            },
        ],
    )
    coinv = app.coinventors.filter(user_id=2001).first()
    assert coinv is not None
    record_withdrawal_consent(
        coinventor_id=coinv.id,
        user_id=2001,
        consent_given=True,
    )

    withdrawn_app = withdraw_application(
        application_id=app.id,
        applicant_user_id=1001,
        reason="Applicant decided not to pursue filing.",
    )
    assert withdrawn_app.status == PatentApplicationStatus.WITHDRAWN.value
    assert withdrawn_app.is_withdrawn is True
    assert withdrawn_app.withdrawal_reason == "Applicant decided not to pursue filing."
    assert withdrawn_app.audit_logs.filter(
        to_state=PatentApplicationStatus.WITHDRAWN.value
    ).exists()


def test_wf_tc_020_bw_pms_16_step_1_guard_withdrawal_missing_reason_or_consent():
    """WF-TC-020 | BW-PMS-16: Step 1 Guard (Withdrawal Eligibility / Reason / Consent Missing).

    Verify withdrawal is not permitted when status is not withdrawal-eligible,
    reason is missing, or required co-inventor consent is lacking.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Guarded Withdrawal App",
        abstract="Application requiring co-inventor consent and reason.",
        detailed_description="Detailed description.",
        claims="1. A method...",
        domain="Software",
        coinventors_data=[
            {
                "user_id": 1001,
                "name": "Lead Inventor",
                "email": "lead@example.test",
                "ownership_percentage": "50.00",
                "agreement_signed": True,
                "consent_given": True,
            },
            {
                "user_id": 2001,
                "name": "Co-Inventor",
                "email": "coinv@example.test",
                "ownership_percentage": "50.00",
            },
        ],
    )

    # Missing co-inventor consent
    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="Valid reason without consent",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.SUBMITTED.value

    # Grant consent, then omit reason
    coinv = app.coinventors.filter(user_id=2001).first()
    assert coinv is not None
    record_withdrawal_consent(
        coinventor_id=coinv.id,
        user_id=2001,
        consent_given=True,
    )

    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.SUBMITTED.value

    # Non-eligible post-filing state
    app.status = PatentApplicationStatus.FILED.value
    app.save(update_fields=["status", "updated_at"])
    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="Attempting withdrawal after filing",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.FILED.value


def test_wf_tc_022_cw_pms_05_step_1_7_candidate_pre_filing_states_withdrawal_coverage():
    """WF-TC-022 | CW-PMS-05: Step 1-7 (Candidate Pre-Filing States Withdrawal Coverage).

    Verify withdrawal across candidate pre-filing states (Submitted, Under
    Review, Needs Revision, Rejected, Approved, Attorney Assigned, Pending
    Review) when configured as eligible.
    """
    for idx, state in enumerate(sorted(WITHDRAWAL_ELIGIBLE_STATES, key=lambda s: s.value)):
        app = submit_application(
            applicant_user_id=1001,
            title=f"Candidate State App {idx}",
            abstract="Pre-filing candidate application.",
            detailed_description="Detailed specification.",
            claims="1. A system...",
            domain="Software",
        )
        app.status = state.value
        app.save(update_fields=["status", "updated_at"])

        withdrawn = withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason=f"Withdrawing from {state.value}",
        )
        assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value
