"""HTTP-only journeys for PMS use cases and named alternate paths.

These complement the endpoint-focused API tests. Each actor acts through the
same authenticated HTTP boundary used by the frontend.
"""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.models import PmsAuditTrail

pytestmark = pytest.mark.django_db

API = "/api/v1/pms"


def _client(stub_iam, user_id: int, role: str, *permissions: str) -> APIClient:
    stub_iam(
        make_session(
            user_id=user_id,
            roles=(role,),
            active_role=role,
            permissions=permissions,
            modules=("pms",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def _submit(client: APIClient, title: str, coinventors: list[dict] | None = None) -> dict:
    response = client.post(
        f"{API}/applications/",
        {
            "title": title,
            "abstract": "A concise technical abstract.",
            "detailed_description": "A detailed description of the invention.",
            "claims": "A device comprising a controller and a sensor.",
            "domain": "Energy Systems",
            "jurisdiction": "IN",
            "coinventors": coinventors or [],
            "documents": [],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def _assign_and_review(
    stub_iam, application_id: int, decision: str, feedback: str = ""
) -> None:
    admin = _client(stub_iam, 9001, "pcc_admin", "pms.application.assign_director")
    assigned = admin.post(
        f"{API}/applications/{application_id}/assign-director/",
        {"director_user_id": 2001},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content
    director = _client(stub_iam, 2001, "director", "pms.application.review")
    reviewed = director.post(
        f"{API}/applications/{application_id}/review/",
        {
            "decision": decision,
            "justification": (
                "The technical evidence and supporting rationale were reviewed in detail."
            ),
            "feedback": feedback,
        },
        format="json",
    )
    assert reviewed.status_code == 201, reviewed.content


def test_uc_pms_003_http_journey_records_coinventor_consent_and_tracks_application(stub_iam):
    """UC-PMS-003 and UC-PMS-002: each inventor signs as self and the applicant tracks status."""
    applicant = _client(
        stub_iam, 1001, "student", "pms.application.create", "pms.application.view_self"
    )
    submitted = _submit(
        applicant,
        "Co-inventor consent journey",
        [
            {
                "user_id": 1001,
                "name": "Lead Inventor",
                "email": "lead@example.test",
                "ownership_percentage": "60.00",
            },
            {
                "user_id": 1002,
                "name": "Co-inventor",
                "email": "co@example.test",
                "ownership_percentage": "40.00",
            },
        ],
    )
    co_inventor_id = next(
        row["id"] for row in submitted["coinventors"] if row["user_id"] == 1002
    )

    co_inventor = _client(stub_iam, 1002, "student", "pms.coinventor.manage")
    consent = co_inventor.post(
        f"{API}/coinventors/{co_inventor_id}/consent/",
        {"consent_given": True, "agreement_signed": True},
        format="json",
    )
    assert consent.status_code == 200, consent.content
    assert consent.json()["consent_given"] is True
    assert consent.json()["agreement_signed"] is True

    applicant = _client(stub_iam, 1001, "student", "pms.application.view_self")
    tracked = applicant.get(f"{API}/applications/{submitted['id']}/")
    assert tracked.status_code == 200, tracked.content
    assert tracked.json()["status"] == "submitted"
    assert any(row["agreement_signed"] for row in tracked.json()["coinventors"])


def test_uc_pms_005_007_008_http_journey_resubmits_and_reaches_approval(stub_iam):
    """UC-PMS-005, UC-PMS-007, UC-PMS-008: revision returns through review."""
    applicant = _client(stub_iam, 1001, "student", "pms.application.create")
    submitted = _submit(applicant, "Revision and reapproval journey")
    _assign_and_review(
        stub_iam,
        submitted["id"],
        "Needs Revision",
        "Clarify the independent claim's sensor calibration method.",
    )

    applicant = _client(
        stub_iam, 1001, "student", "pms.application.revise", "pms.application.view_self"
    )
    revision = applicant.post(
        f"{API}/applications/{submitted['id']}/revise/",
        {
            "feedback_response": "The independent claim now states the calibration method.",
            "claims": "A calibrated device comprising the controller and sensor.",
        },
        format="json",
    )
    assert revision.status_code == 200, revision.content
    assert revision.json()["status"] == "resubmitted"

    admin = _client(stub_iam, 9001, "pcc_admin", "pms.application.assign_director")
    reassigned = admin.post(
        f"{API}/applications/{submitted['id']}/assign-director/",
        {"director_user_id": 2001},
        format="json",
    )
    assert reassigned.status_code == 200, reassigned.content
    director = _client(stub_iam, 2001, "director", "pms.application.review")
    approval = director.post(
        f"{API}/applications/{submitted['id']}/review/",
        {
            "decision": "Approve",
            "justification": "The revised claims address the review feedback with adequate detail.",
        },
        format="json",
    )
    assert approval.status_code == 201, approval.content
    applicant = _client(stub_iam, 1001, "student", "pms.application.view_self")
    tracked = applicant.get(f"{API}/applications/{submitted['id']}/")
    assert tracked.status_code == 200, tracked.content
    assert tracked.json()["status"] == "approved"


def test_uc_pms_005_br_pms_034_rejected_application_revision_alternate(stub_iam):
    """UC-PMS-005 and BR-PMS-034: an Applicant can revise a rejected application."""
    submitted = _submit(
        _client(stub_iam, 1001, "student", "pms.application.create"),
        "Rejected revision alternate journey",
    )
    _assign_and_review(stub_iam, submitted["id"], "Reject")

    applicant = _client(
        stub_iam,
        1001,
        "student",
        "pms.application.revise",
        "pms.application.view_self",
    )
    revised = applicant.post(
        f"{API}/applications/{submitted['id']}/revise/",
        {
            "feedback_response": "The revised claims respond to the rejection grounds with specific evidence.",
            "claims": "A sensor system with a calibrated feedback controller.",
        },
        format="json",
    )
    assert revised.status_code == 200, revised.content
    assert revised.json()["status"] == "resubmitted"
    assert revised.json()["claims"].startswith("A sensor system")
    assert PmsAuditTrail.objects.filter(
        application_id=submitted["id"],
        action_type="application_resubmitted",
        from_state="rejected",
        to_state="resubmitted",
    ).exists()


def test_uc_pms_010_011_http_journey_declines_and_reassigns_attorney(stub_iam):
    """UC-PMS-010, UC-PMS-011: decline is recorded, then a new offer is accepted."""
    application = _submit(
        _client(stub_iam, 1001, "student", "pms.application.create"),
        "Attorney reassignment journey",
    )
    _assign_and_review(stub_iam, application["id"], "Approve")

    admin = _client(stub_iam, 9001, "pcc_admin", "pms.attorney.assign", "pms.panel.manage")
    for attorney_id in (5001, 5002):
        panel = admin.post(
            f"{API}/attorney-panel/",
            {
                "attorney_user_id": attorney_id,
                "name": f"Attorney {attorney_id}",
                "email": f"attorney{attorney_id}@example.test",
                "expertise_domains": ["Energy Systems"],
            },
            format="json",
        )
        assert panel.status_code == 201, panel.content

    first_offer = admin.post(
        f"{API}/applications/{application['id']}/assign-attorney/",
        {"attorney_user_id": 5001},
        format="json",
    )
    assert first_offer.status_code == 201, first_offer.content
    declined = _client(stub_iam, 5001, "attorney", "pms.attorney.respond_assignment").post(
        f"{API}/attorney-assignments/{first_offer.json()['id']}/respond/",
        {"accept": False, "decline_reason": "Current workload prevents timely handling."},
        format="json",
    )
    assert declined.status_code == 200, declined.content
    assert declined.json()["status"] == "declined"

    admin = _client(stub_iam, 9001, "pcc_admin", "pms.attorney.assign")
    second_offer = admin.post(
        f"{API}/applications/{application['id']}/assign-attorney/",
        {"attorney_user_id": 5002},
        format="json",
    )
    assert second_offer.status_code == 201, second_offer.content
    accepted = _client(stub_iam, 5002, "attorney", "pms.attorney.respond_assignment").post(
        f"{API}/attorney-assignments/{second_offer.json()['id']}/respond/",
        {"accept": True},
        format="json",
    )
    assert accepted.status_code == 200, accepted.content
    assert accepted.json()["status"] == "accepted"


def test_uc_pms_032_http_journey_reads_scoped_workflow_oversight(stub_iam):
    """UC-PMS-032: a Director reads workflow oversight only within authorization scope."""
    application = _submit(
        _client(stub_iam, 1001, "student", "pms.application.create"),
        "Workflow oversight journey",
    )
    admin = _client(stub_iam, 9001, "pcc_admin", "pms.application.assign_director")
    assigned = admin.post(
        f"{API}/applications/{application['id']}/assign-director/",
        {"director_user_id": 2001},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content

    admin = _client(stub_iam, 9001, "pcc_admin", "pms.workflow.monitor")
    monitored = admin.get(f"{API}/workflow-oversight/")
    assert monitored.status_code == 200, monitored.content
    admin_row = next(row for row in monitored.json() if row["application_id"] == application["id"])
    assert admin_row["status"] == "under_review"

    director = _client(stub_iam, 2001, "director", "pms.workflow.oversight")
    scoped = director.get(f"{API}/workflow-oversight/")
    assert scoped.status_code == 200, scoped.content
    assert any(row["application_id"] == application["id"] for row in scoped.json())


def test_uc_pms_030_031_http_journey_keeps_reports_in_actor_scope(stub_iam):
    """UC-PMS-030, UC-PMS-031: Applicant and Director reports return only visible rows."""
    applicant = _submit(
        _client(stub_iam, 1001, "student", "pms.application.create"),
        "Applicant personal report",
    )
    _submit(
        _client(stub_iam, 1002, "student", "pms.application.create"),
        "Other applicant report",
    )
    assigned = _client(stub_iam, 9001, "pcc_admin", "pms.application.assign_director").post(
        f"{API}/applications/{applicant['id']}/assign-director/",
        {"director_user_id": 2001},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content

    own_report = _client(stub_iam, 1001, "student", "pms.report.view_self").get(
        f"{API}/reports/"
    )
    assert own_report.status_code == 200, own_report.content
    assert own_report.json()["total_applications"] == 1

    director_report = _client(stub_iam, 2001, "director", "pms.report.view").get(
        f"{API}/reports/"
    )
    assert director_report.status_code == 200, director_report.content
    assert director_report.json()["total_applications"] == 1


def test_uc_pms_033_http_journey_records_advice_for_assigned_attorney(stub_iam):
    """UC-PMS-033: advice is written only after approval and accepted assignment."""
    application = _submit(
        _client(stub_iam, 1001, "student", "pms.application.create"),
        "Legal advice journey",
    )
    _assign_and_review(stub_iam, application["id"], "Approve")

    admin = _client(stub_iam, 9001, "pcc_admin", "pms.panel.manage", "pms.attorney.assign")
    panel = admin.post(
        f"{API}/attorney-panel/",
        {
            "attorney_user_id": 5001,
            "name": "Assigned Counsel",
            "email": "assigned-counsel@example.test",
            "expertise_domains": ["Energy Systems"],
        },
        format="json",
    )
    assert panel.status_code == 201, panel.content
    offer = admin.post(
        f"{API}/applications/{application['id']}/assign-attorney/",
        {"attorney_user_id": 5001},
        format="json",
    )
    assert offer.status_code == 201, offer.content
    accepted = _client(stub_iam, 5001, "attorney", "pms.attorney.respond_assignment").post(
        f"{API}/attorney-assignments/{offer.json()['id']}/respond/",
        {"accept": True},
        format="json",
    )
    assert accepted.status_code == 200, accepted.content

    attorney = _client(stub_iam, 5001, "attorney", "pms.advice.record")
    advice = attorney.post(
        f"{API}/applications/{application['id']}/legal-advice/",
        {
            "stage": "review",
            "advice_text": "Claims should emphasize the control loop's novelty over cited prior art.",
        },
        format="json",
    )
    assert advice.status_code == 201, advice.content
    assert advice.json()["stage"] == "review"
    assert advice.json()["advice_text"].startswith("Claims should emphasize")


def test_uc_pms_014_015_029_br_pms_065_http_office_action_review_journey(stub_iam):
    """UC-PMS-014, UC-PMS-015, UC-PMS-029, BR-PMS-065 cover response submission."""
    application = _submit(
        _client(stub_iam, 1001, "student", "pms.application.create"),
        "Office action applicant review journey",
    )
    _assign_and_review(stub_iam, application["id"], "Approve")

    admin = _client(stub_iam, 9001, "pcc_admin", "pms.panel.manage", "pms.attorney.assign")
    panel = admin.post(
        f"{API}/attorney-panel/",
        {
            "attorney_user_id": 5001,
            "name": "Office Action Counsel",
            "email": "office-action-counsel@example.test",
            "expertise_domains": ["Energy Systems"],
        },
        format="json",
    )
    assert panel.status_code == 201, panel.content
    offer = admin.post(
        f"{API}/applications/{application['id']}/assign-attorney/",
        {"attorney_user_id": 5001},
        format="json",
    )
    assert offer.status_code == 201, offer.content
    accepted = _client(stub_iam, 5001, "attorney", "pms.attorney.respond_assignment").post(
        f"{API}/attorney-assignments/{offer.json()['id']}/respond/",
        {"accept": True},
        format="json",
    )
    assert accepted.status_code == 200, accepted.content

    budget_actor = _client(stub_iam, 2001, "director", "pms.budget.review")
    proposed = budget_actor.put(
        f"{API}/applications/{application['id']}/budget/",
        {"filing_fees": "12000.00", "attorney_fees": "25000.00", "administrative_costs": "3000.00"},
        format="json",
    )
    assert proposed.status_code == 200, proposed.content
    decided = budget_actor.post(
        f"{API}/applications/{application['id']}/budget/",
        {"decision": "Approve", "justification": "The listed costs are supported and approved."},
        format="json",
    )
    assert decided.status_code == 200, decided.content
    assert decided.json()["status"] == "approved"

    attorney = _client(stub_iam, 5001, "attorney", "pms.filing.record")
    filing = attorney.post(
        f"{API}/applications/{application['id']}/filing/",
        {
            "external_filing_id": "TEST-PMS-OA-001",
            "external_filing_date": "2026-11-21",
            "filing_confirmation": "Filing acknowledgement recorded by the Attorney.",
        },
        format="json",
    )
    assert filing.status_code == 200, filing.content
    assert filing.json()["status"] == "filed"

    recorded = attorney.post(
        f"{API}/applications/{application['id']}/office-actions/",
        {
            "action_type": "Examination Report",
            "issue_date": "2026-11-22",
            "due_date": "2027-02-22",
            "details": "The examiner requests clarification of claim scope.",
            "requires_applicant_review": True,
        },
        format="json",
    )
    assert recorded.status_code == 201, recorded.content
    office_action_id = recorded.json()["id"]
    drafted = attorney.post(
        f"{API}/office-actions/{office_action_id}/draft-response/",
        {"draft_response": "The amended claim clarifies the sensor calibration boundary."},
        format="json",
    )
    assert drafted.status_code == 200, drafted.content
    assert drafted.json()["status"] == "awaiting_applicant_approval"

    applicant = _client(stub_iam, 1001, "student", "pms.office_action.review")
    approved = applicant.post(f"{API}/office-actions/{office_action_id}/approve-response/")
    assert approved.status_code == 200, approved.content
    assert approved.json()["applicant_approved"] is True

    attorney = _client(stub_iam, 5001, "attorney", "pms.office_action.respond")
    response = attorney.post(
        f"{API}/office-actions/{office_action_id}/submit-response/",
        {"submission_details": "The Attorney recorded external response submission."},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "response_submitted"
    assert PmsAuditTrail.objects.filter(
        application_id=application["id"], action_type="office_action_applicant_approved"
    ).exists()
    assert PmsAuditTrail.objects.filter(
        application_id=application["id"], action_type="office_action_response_submitted"
    ).exists()
