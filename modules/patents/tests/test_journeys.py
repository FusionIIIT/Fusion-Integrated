"""Multi-actor HTTP journey test suites (R1-04, R1-12)."""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    AttorneyPanelMember,
    PatentApplication,
    PatentPolicy,
)
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service

pytestmark = pytest.mark.django_db


class DummyActor:
    def __init__(self, user_id=1, roles=("student",), permissions=()):
        self.user_id = user_id
        self.roles = roles
        self.permissions = set(permissions)

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions


def as_actor(stub_iam, client: APIClient, user_id=101, permissions=(), roles=("student",)):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="student",
            roles=roles,
            active_role=roles[0] if roles else None,
            modules=("patents",),
            permissions=permissions,
        )
    )
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")


def test_main_lifecycle_journey(stub_iam):
    client = APIClient()
    PatentPolicy.objects.create(
        is_active=True,
        cost_escalation_threshold=Decimal("150000.00"),
        withdrawal_eligible_states=[sm.DRAFT, sm.SUBMITTED],
        max_attorney_workload=5,
    )
    AttorneyPanelMember.objects.create(
        user_id=401,
        firm_name="Apex IP Attorneys",
        expertise_domains=["Quantum", "Nanotechnology"],
        is_approved_panel=True,
        active_workload=0,
    )

    # UC-PMS-001 & BR-PMS-017: Applicant submits new patent application
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE),
        roles=("student",),
    )
    create_resp = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Quantum Error Correction Transmon",
            "abstract": "A novel topological surface code layout for superconducting qubits.",
            "description": "Comprehensive specification describing microwave resonator coupling.",
            "claims": "1. A circuit comprising at least five coupled transmons.",
            "co_inventors": [
                {
                    "name": "Dr. Sarah Rao",
                    "email": "sarah.rao@example.edu",
                    "share_percentage": "100.00",
                    "user_id": 102,
                }
            ],
        },
        format="json",
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    app_id = create_resp.data["id"]

    # Move to SUBMITTED
    app_obj = PatentApplication.objects.get(pk=app_id)
    app_obj.status = sm.SUBMITTED
    app_obj.save()

    # UC-PMS-002, UC-PMS-030 & BR-PMS-003: Applicant views own application and report
    list_resp = client.get("/api/v1/patents/applications")
    assert list_resp.status_code == status.HTTP_200_OK
    items = list_resp.data.get("results", list_resp.data) if isinstance(list_resp.data, dict) else list_resp.data
    assert any(item["id"] == app_id for item in items)

    # UC-PMS-003, BR-PMS-020, BR-PMS-073, BR-PMS-074, BR-PMS-075, BR-PMS-078: Co-inventor grants consent
    as_actor(
        stub_iam,
        client,
        user_id=102,
        permissions=(p.P_APPLICATION_VIEW_SELF,),
        roles=("faculty",),
    )
    consent_resp = client.post(f"/api/v1/patents/applications/{app_id}/consent")
    assert consent_resp.status_code == status.HTTP_200_OK
    assert consent_resp.data["consent_recorded"] is True

    # UC-PMS-019, BR-PMS-014, BR-PMS-015, BR-PMS-016, BR-PMS-082, BR-PMS-084, BR-PMS-086, BR-PMS-140: Upload specification document
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_UPDATE),
        roles=("student",),
    )
    doc_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/documents",
        {
            "document_type": "specification",
            "file_name": "quantum_patent_spec.pdf",
        },
        format="json",
    )
    assert doc_resp.status_code == status.HTTP_201_CREATED

    # UC-PMS-004 & BR-PMS-141: Search prior art
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_PRIOR_ART_SEARCH),
        roles=("student",),
    )
    art_resp = client.post(
        "/api/v1/patents/prior-art/search",
        {"query": "transmon"},
        format="json",
    )
    assert art_resp.status_code == status.HTTP_200_OK
    assert "results" in art_resp.data

    # UC-PMS-007, BR-PMS-022, BR-PMS-023, BR-PMS-024, BR-PMS-025, BR-PMS-026, BR-PMS-027, BR-PMS-097, BR-PMS-126, BR-PMS-130, BR-PMS-131: Admin assigns Director
    as_actor(
        stub_iam,
        client,
        user_id=901,
        permissions=(
            p.P_APPLICATION_VIEW,
            p.P_APPLICATION_ASSIGN_DIRECTOR,
            p.P_ATTORNEY_ASSIGN,
            p.P_PANEL_MANAGE,
            p.P_AUDIT_VIEW,
        ),
        roles=("pcc_admin",),
    )
    assign_dir_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/assign-director",
        {"director_id": 201},
        format="json",
    )
    assert assign_dir_resp.status_code == status.HTTP_200_OK
    assert assign_dir_resp.data["status"] == sm.UNDER_REVIEW

    # UC-PMS-008, BR-PMS-029, BR-PMS-030, BR-PMS-031: Director reviews and approves application
    as_actor(
        stub_iam,
        client,
        user_id=201,
        permissions=(
            p.P_APPLICATION_VIEW,
            p.P_APPLICATION_REVIEW,
            p.P_BUDGET_APPROVE,
            p.P_REPORT_VIEW,
            p.P_MAINTENANCE_DECIDE,
        ),
        roles=("director",),
    )
    rev_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/review-decision",
        {
            "decision": "APPROVE",
            "justification": "Novelty, inventiveness, and industrial applicability confirmed across all claims.",
        },
        format="json",
    )
    assert rev_resp.status_code == status.HTTP_200_OK
    assert rev_resp.data["decision"] == "APPROVE"

    # UC-PMS-009, BR-PMS-048, BR-PMS-049, BR-PMS-050, BR-PMS-051, BR-PMS-052, BR-PMS-053, BR-PMS-139: Record and approve budget
    admin_actor = DummyActor(user_id=901, roles=("pcc_admin",))
    budget_entry = budget_service.record_budget_entry(
        actor=admin_actor,
        application_id=app_id,
        entry_type="FILING_FEE",
        amount=Decimal("45000.00"),
        category="GOVERNMENT_FEE",
        notes="Official IPO filing fees.",
    )
    budget_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/budget-decision",
        {
            "decision": "APPROVE",
            "budget_entry_id": budget_entry.id,
            "notes": "Approved under FY26 research budget allocation.",
        },
        format="json",
    )
    assert budget_resp.status_code == status.HTTP_200_OK
    assert budget_resp.data["status"] == "APPROVED"

    # UC-PMS-010, BR-PMS-040, BR-PMS-041, BR-PMS-042, BR-PMS-043, BR-PMS-044, BR-PMS-045, BR-PMS-127: PCC Admin assigns approved attorney
    as_actor(
        stub_iam,
        client,
        user_id=901,
        permissions=(p.P_APPLICATION_VIEW, p.P_ATTORNEY_ASSIGN),
        roles=("pcc_admin",),
    )
    assign_att_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/assign-attorney",
        {"attorney_id": 401},
        format="json",
    )
    assert assign_att_resp.status_code == status.HTTP_200_OK
    assert assign_att_resp.data["status"] == sm.ASSIGNMENT_OFFERED

    # UC-PMS-011: Attorney accepts assignment
    as_actor(
        stub_iam,
        client,
        user_id=401,
        permissions=(
            p.P_APPLICATION_VIEW,
            p.P_ATTORNEY_RESPOND_ASSIGNMENT,
            p.P_ASSESSMENT_PERFORM,
            p.P_FILING_RECORD,
            p.P_OFFICE_ACTION_RECORD,
            p.P_OFFICE_ACTION_RESPOND,
        ),
        roles=("attorney",),
    )
    accept_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/respond-assignment",
        {"action": "accept"},
        format="json",
    )
    assert accept_resp.status_code == status.HTTP_200_OK
    assert accept_resp.data["status"] == sm.ATTORNEY_ASSIGNED

    # UC-PMS-012 & BR-PMS-046: Attorney starts patentability assessment
    assess_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/assessment",
        {"action": "start"},
        format="json",
    )
    assert assess_resp.status_code == status.HTTP_200_OK
    assert assess_resp.data["status"] == sm.ASSESSMENT_IN_PROGRESS

    # UC-PMS-013, BR-PMS-055, BR-PMS-056, BR-PMS-138, BR-PMS-142: Record external patent filing
    filing_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/filing",
        {
            "filing_number": "IN20261109988",
            "filing_office": "IPO-Delhi",
            "jurisdiction": "IN",
            "notes": "Formal complete specification filed with priority claim.",
        },
        format="json",
    )
    assert filing_resp.status_code == status.HTTP_200_OK
    assert filing_resp.data["status"] == sm.FILED

    # UC-PMS-014, BR-PMS-065, BR-PMS-066, BR-PMS-099: Log office action communication
    oa_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/office-actions",
        {
            "action_code": "FER-1",
            "issuing_authority": "Indian Patent Office",
            "issued_date": str(timezone.now().date()),
            "response_deadline": str(timezone.now().date() + datetime.timedelta(days=180)),
            "summary": "First Examination Report citing prior art reference D1.",
            "requires_applicant_review": True,
        },
        format="json",
    )
    assert oa_resp.status_code == status.HTTP_201_CREATED
    oa_id = oa_resp.data["id"]

    # UC-PMS-015: Attorney drafts response to office action
    oa_reply_resp = client.post(
        f"/api/v1/patents/office-actions/{oa_id}/response",
        {"response_summary": "Distinguished independent claim 1 over cited reference D1."},
        format="json",
    )
    assert oa_reply_resp.status_code == status.HTTP_200_OK

    # UC-PMS-029 & BR-PMS-146: Applicant approves response
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_OFFICE_ACTION_APPROVE),
        roles=("student",),
    )
    approve_oa_resp = client.post(f"/api/v1/patents/office-actions/{oa_id}/approve")
    assert approve_oa_resp.status_code == status.HTTP_200_OK
    assert approve_oa_resp.data["status"] == "RESPONSE_READY"

    # Transition application to GRANTED directly to test post-grant maintenance
    app_obj = PatentApplication.objects.get(pk=app_id)
    app_obj.status = sm.GRANTED
    app_obj.grant_date = timezone.now().date()
    app_obj.save()

    # UC-PMS-017, UC-PMS-018, BR-PMS-059, BR-PMS-060, BR-PMS-061, BR-PMS-100: Director records renewal decision
    as_actor(
        stub_iam,
        client,
        user_id=201,
        permissions=(p.P_APPLICATION_VIEW, p.P_MAINTENANCE_DECIDE, p.P_REPORT_VIEW),
        roles=("director",),
    )
    renew_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/renewal-decision",
        {"renew": True, "notes": "Commercial potential active; renew 3rd year annuity."},
        format="json",
    )
    assert renew_resp.status_code == status.HTTP_200_OK

    # UC-PMS-020, UC-PMS-021, BR-PMS-088, BR-PMS-091: Tech transfer licensing request
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_TECH_TRANSFER_CREATE),
        roles=("student",),
    )
    tt_resp = client.post(
        "/api/v1/patents/tech-transfer",
        {
            "application_id": app_id,
            "request_type": "EXCLUSIVE_LICENSE",
            "partner_name": "Quantum Spin-off Labs Ltd.",
            "terms_summary": "5.50% royalty rate on telecom devices.",
        },
        format="json",
    )
    assert tt_resp.status_code == status.HTTP_201_CREATED

    # UC-PMS-024, UC-PMS-031, BR-PMS-005, BR-PMS-006: System-wide reports
    as_actor(
        stub_iam,
        client,
        user_id=201,
        permissions=(p.P_APPLICATION_VIEW, p.P_REPORT_VIEW),
        roles=("director",),
    )
    reports_resp = client.get("/api/v1/patents/reports")
    assert reports_resp.status_code == status.HTTP_200_OK
    assert "total_applications" in reports_resp.data

    # UC-PMS-026 & UC-PMS-028, BR-PMS-121, BR-PMS-122: PCC Admin views attorney panel and audit logs
    as_actor(
        stub_iam,
        client,
        user_id=901,
        permissions=(p.P_PANEL_MANAGE, p.P_AUDIT_VIEW),
        roles=("pcc_admin",),
    )
    panel_resp = client.get("/api/v1/patents/attorney-panel")
    assert panel_resp.status_code == status.HTTP_200_OK
    assert len(panel_resp.data) >= 1

    audit_resp = client.get("/api/v1/patents/audit-logs")
    assert audit_resp.status_code == status.HTTP_200_OK
    assert "audit_logs" in audit_resp.data


def test_revision_and_resubmission_journey(stub_iam):
    client = APIClient()
    PatentPolicy.objects.create(is_active=True, revision_resubmission_days=60)

    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE, p.P_APPLICATION_UPDATE),
        roles=("student",),
    )
    res = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Graphene Battery Cathode",
            "abstract": "High capacity cathode using exfoliation.",
            "description": "Initial specification.",
            "claims": "1. A cathode material.",
            "co_inventors": [],
        },
        format="json",
    )
    app_id = res.data["id"]

    # Transition to SUBMITTED
    app = PatentApplication.objects.get(pk=app_id)
    app.status = sm.SUBMITTED
    app.save()

    # Assign director
    as_actor(
        stub_iam,
        client,
        user_id=901,
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_ASSIGN_DIRECTOR),
        roles=("pcc_admin",),
    )
    client.post(
        f"/api/v1/patents/applications/{app_id}/assign-director",
        {"director_id": 201},
        format="json",
    )

    # Director returns Needs Revision
    as_actor(
        stub_iam,
        client,
        user_id=201,
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_REVIEW),
        roles=("director",),
    )
    rev_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/review-decision",
        {
            "decision": "NEEDS_REVISION",
            "justification": "Prior art disclosure requires clarification in independent claims.",
        },
        format="json",
    )
    assert rev_resp.status_code == status.HTTP_200_OK
    assert rev_resp.data["decision"] == "NEEDS_REVISION"

    # UC-PMS-005, BR-PMS-033, BR-PMS-034, BR-PMS-035, BR-PMS-036, BR-PMS-087, BR-PMS-098: Applicant updates and resubmits
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_UPDATE),
        roles=("student",),
    )
    update_resp = client.put(
        f"/api/v1/patents/applications/{app_id}",
        {
            "title": "Graphene Battery Cathode (Revised)",
            "abstract": "High capacity cathode with enhanced exfoliation.",
            "description": "Updated detailed specification clarifying chemical etching step.",
            "claims": "1. A cathode material comprising exfoliated graphene sheets.",
        },
        format="json",
    )
    assert update_resp.status_code == status.HTTP_200_OK

    # Resubmit application
    app_service.transition_application(
        app_id,
        "resubmit",
        actor=DummyActor(user_id=101, permissions=[p.P_APPLICATION_VIEW_SELF]),
    )
    app.refresh_from_db()
    assert app.status == sm.RESUBMITTED


def test_rejection_and_appeal_journey(stub_iam):
    client = APIClient()
    PatentPolicy.objects.create(is_active=True)

    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(
            p.P_APPLICATION_VIEW_SELF,
            p.P_APPLICATION_CREATE,
            p.P_APPLICATION_APPEAL,
        ),
        roles=("student",),
    )
    res = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Perovskite Photovoltaic Cell",
            "abstract": "Efficiency enhancement.",
            "description": "Description.",
            "claims": "Claims.",
            "co_inventors": [],
        },
        format="json",
    )
    app_id = res.data["id"]

    # Transition to SUBMITTED
    app = PatentApplication.objects.get(pk=app_id)
    app.status = sm.SUBMITTED
    app.save()

    # Assign director and reject
    as_actor(
        stub_iam,
        client,
        user_id=901,
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_ASSIGN_DIRECTOR),
        roles=("pcc_admin",),
    )
    client.post(
        f"/api/v1/patents/applications/{app_id}/assign-director",
        {"director_id": 201},
        format="json",
    )

    as_actor(
        stub_iam,
        client,
        user_id=201,
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_REVIEW, p.P_APPLICATION_DECIDE_APPEAL),
        roles=("director",),
    )
    client.post(
        f"/api/v1/patents/applications/{app_id}/review-decision",
        {
            "decision": "REJECT",
            "justification": "Substantial overlap with preexisting institute disclosure D09.",
        },
        format="json",
    )

    # UC-PMS-022, BR-PMS-092, BR-PMS-093, BR-PMS-094: Applicant files appeal
    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_APPEAL),
        roles=("student",),
    )
    appeal_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/appeal",
        {
            "grounds": "The cited disclosure D09 does not disclose the active passivation layer.",
        },
        format="json",
    )
    assert appeal_resp.status_code == status.HTTP_200_OK

    # UC-PMS-023 & BR-PMS-095: Director reviews appeal and remands for amendment
    as_actor(
        stub_iam,
        client,
        user_id=201,
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_DECIDE_APPEAL),
        roles=("director",),
    )
    decide_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/appeal-decision",
        {
            "outcome": "REMAND",
            "justification": "Remanding application to allow applicant to amend claims around passivation.",
        },
        format="json",
    )
    assert decide_resp.status_code == status.HTTP_200_OK


def test_withdrawal_journey(stub_iam):
    # UC-PMS-006, BR-PMS-067, BR-PMS-068, BR-PMS-069, BR-PMS-070: Applicant withdraws before filing
    client = APIClient()
    PatentPolicy.objects.create(withdrawal_eligible_states=[sm.DRAFT, sm.SUBMITTED], is_active=True)

    as_actor(
        stub_iam,
        client,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE, p.P_APPLICATION_WITHDRAW),
        roles=("student",),
    )
    res = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Bio-sensor Array",
            "abstract": "Abstract",
            "description": "Description",
            "claims": "Claims",
            "co_inventors": [],
        },
        format="json",
    )
    app_id = res.data["id"]

    withdraw_resp = client.post(
        f"/api/v1/patents/applications/{app_id}/withdraw",
        {"reason": "Commercial sponsor cancelled joint research project."},
        format="json",
    )
    assert withdraw_resp.status_code == status.HTTP_200_OK
    assert withdraw_resp.data["status"] == sm.WITHDRAWN


def test_deadlines_and_oversight_journey():
    # UC-PMS-016, UC-PMS-025, UC-PMS-027, UC-PMS-032, UC-PMS-033, BR-PMS-076, BR-PMS-077, BR-PMS-101, BR-PMS-102, BR-PMS-103, BR-PMS-104, BR-PMS-116
    from modules.patents.domain import deadlines
    base_date = datetime.date(2026, 6, 1)
    assert deadlines.match_alert_interval(datetime.date(2026, 7, 1), base_date) == 30
    assert deadlines.match_alert_interval(datetime.date(2026, 6, 16), base_date) == 15
    assert deadlines.match_alert_interval(datetime.date(2026, 6, 6), base_date) == 5
