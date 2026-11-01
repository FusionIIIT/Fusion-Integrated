"""Integration tests for Patent Management System API layer."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.constants import STATUS_APPROVED, STATUS_SUBMITTED
from modules.pms.models import (
    AttorneyPanel,
    PatentApplication,
)

pytestmark = pytest.mark.django_db


def _make_client(stub_iam, user_id=1001, permissions=(), roles=("student",)):
    stub_iam(
        make_session(
            user_id=user_id,
            modules=("pms",),
            permissions=permissions,
            roles=roles,
            active_role=roles[0] if roles else "student",
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return c


class TestApplicationApi:
    def test_submit_and_list_application(self, stub_iam):
        client = _make_client(
            stub_iam,
            user_id=1001,
            permissions=("pms.application.view", "pms.application.create"),
        )

        payload = {
            "title": "Novel Drone Navigation System",
            "abstract": "An autonomous sensor fusion pipeline for GPS-denied environments.",
            "description": "Full technical description of algorithms and hardware sensors.",
            "claims": "1. An autonomous navigation system comprising...",
            "domain": "Aerospace & Robotics",
            "keywords": "drone, navigation, slam",
            "inventors": [
                {
                    "user_id": 1001,
                    "name": "Prof. Rao",
                    "email": "rao@inst.ac.in",
                    "department": "Aerospace",
                    "inventor_type": "faculty",
                    "percentage_share": "100.00",
                    "is_primary": True,
                }
            ],
        }

        # 1. POST create application
        res = client.post("/api/v1/pms/applications", data=payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED, res.data
        data = res.json()
        assert data["title"] == payload["title"]
        assert data["application_no"].startswith("PMS-")
        assert data["status"] == STATUS_SUBMITTED
        app_id = data["id"]

        # 2. GET list applications
        list_res = client.get("/api/v1/pms/applications")
        assert list_res.status_code == status.HTTP_200_OK
        results = list_res.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == app_id

        # 3. GET application detail
        detail_res = client.get(f"/api/v1/pms/applications/{app_id}")
        assert detail_res.status_code == status.HTTP_200_OK
        assert len(detail_res.json()["inventors"]) == 1

    def test_row_level_scoping_applicant_isolation(self, stub_iam):
        # Applicant 1 creates an application
        c1 = _make_client(
            stub_iam,
            user_id=1001,
            permissions=("pms.application.view", "pms.application.create"),
        )
        app1 = PatentApplication.objects.create(
            user_id=1001,
            title="App 1",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="CSE",
            status=STATUS_SUBMITTED,
        )

        # Applicant 2 creates an application
        app2 = PatentApplication.objects.create(
            user_id=2002,
            title="App 2",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="ECE",
            status=STATUS_SUBMITTED,
        )

        # User 1 views list -> sees only app1
        res1 = c1.get("/api/v1/pms/applications")
        ids1 = [r["id"] for r in res1.json()["results"]]
        assert ids1 == [app1.id]

        # User 1 tries to GET app2 -> 404 (absent from scope)
        detail_res1 = c1.get(f"/api/v1/pms/applications/{app2.id}")
        assert detail_res1.status_code == status.HTTP_404_NOT_FOUND

        # Switch to User 2
        c2 = _make_client(
            stub_iam,
            user_id=2002,
            permissions=("pms.application.view",),
        )
        res2 = c2.get("/api/v1/pms/applications")
        ids2 = [r["id"] for r in res2.json()["results"]]
        assert ids2 == [app2.id]

        # Switch to PCC Admin (has pms.application.assign / admin view) -> sees both
        c_admin = _make_client(
            stub_iam,
            user_id=9999,
            permissions=("pms.application.view", "pms.application.assign"),
            roles=("staff",),
        )
        res_admin = c_admin.get("/api/v1/pms/applications")
        ids_admin = [r["id"] for r in res_admin.json()["results"]]
        assert app1.id in ids_admin and app2.id in ids_admin

    def test_forbidden_without_module_grant_or_permission(self, stub_iam):
        # Client without module grant
        stub_iam(
            make_session(
                user_id=1001,
                modules=("other_module",),
                permissions=("pms.application.view",),
            )
        )
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        res = c.get("/api/v1/pms/applications")
        assert res.status_code == status.HTTP_403_FORBIDDEN


class TestDirectorAndReviewApi:
    def test_assign_director_and_review(self, stub_iam):
        app = PatentApplication.objects.create(
            user_id=1001,
            title="Biofuel Reactor",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="Chemical",
            status=STATUS_SUBMITTED,
        )

        # 1. PCC Admin assigns Director
        c_admin = _make_client(
            stub_iam,
            user_id=8888,
            permissions=("pms.application.view", "pms.application.assign"),
            roles=("staff",),
        )
        assign_res = c_admin.post(
            f"/api/v1/pms/applications/{app.id}/assign-director",
            data={"director_user_id": 9001},
            format="json",
        )
        assert assign_res.status_code == status.HTTP_200_OK, assign_res.data
        app.refresh_from_db()
        assert app.status == "under_review"

        # 2. Director reviews and approves
        c_director = _make_client(
            stub_iam,
            user_id=9001,
            permissions=("pms.application.view", "pms.application.review"),
            roles=("Director",),
        )
        review_payload = {
            "decision": "approve",
            "justification": "The biofuel reactor demonstrates clear novelty, significant industrial applicability, and qualifies for full patent prosecution support.",
        }
        rev_res = c_director.post(
            f"/api/v1/pms/applications/{app.id}/review",
            data=review_payload,
            format="json",
        )
        assert rev_res.status_code == status.HTTP_200_OK, rev_res.data
        app.refresh_from_db()
        assert app.status == STATUS_APPROVED


class TestAttorneyAndBudgetApi:
    def test_budget_and_attorney_workflow(self, stub_iam):
        app = PatentApplication.objects.create(
            user_id=1001,
            title="Quantum Cryptographic Router",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="Computer Science",
            status=STATUS_APPROVED,
        )

        # 1. Setup Attorney Panel
        AttorneyPanel.objects.create(
            user_id=7001,
            name="Adv. Mehra",
            firm_name="Mehra IP Law",
            email="mehra@iplaw.in",
            specialization="Computer Science",
            is_active=True,
            max_workload=5,
            current_workload=0,
        )

        # 2. PCC Admin assigns attorney
        c_admin = _make_client(
            stub_iam,
            user_id=8888,
            permissions=(
                "pms.application.view",
                "pms.attorney.assign",
                "pms.budget.view",
                "pms.budget.manage",
            ),
            roles=("staff",),
        )
        assign_res = c_admin.post(
            f"/api/v1/pms/applications/{app.id}/assign-attorney",
            data={"attorney_user_id": 7001},
            format="json",
        )
        assert assign_res.status_code == status.HTTP_200_OK, assign_res.data
        assignment_id = assign_res.json()["id"]

        # 3. Attorney accepts assignment
        c_attorney = _make_client(
            stub_iam,
            user_id=7001,
            permissions=("pms.application.view", "pms.attorney.review"),
            roles=("staff",),
        )
        respond_res = c_attorney.post(
            f"/api/v1/pms/attorney/assignments/{assignment_id}/respond",
            data={"accept": True, "remarks": "Accepted for prosecution."},
            format="json",
        )
        assert respond_res.status_code == status.HTTP_200_OK, respond_res.data

        # 4. Attorney records patentability assessment
        assess_payload = {
            "recommendation": "file_patent",
            "novelty_analysis": "Novel key distribution protocol over noisy fiber channels.",
            "inventive_step_analysis": "Non-obvious error correction matrix with low latency.",
            "industrial_applicability": "Direct application in high-security datacenter interconnects.",
            "prior_art_findings": "Searched IEEE Xplore, Google Patents. No conflicting art.",
            "detailed_opinion": "Strong patentability prospects in India and USPTO.",
        }
        assess_res = c_attorney.post(
            f"/api/v1/pms/applications/{app.id}/assessment",
            data=assess_payload,
            format="json",
        )
        assert assess_res.status_code == status.HTTP_200_OK, assess_res.data

        # 5. PCC Admin creates budget
        _make_client(
            stub_iam,
            user_id=8888,
            permissions=(
                "pms.application.view",
                "pms.attorney.assign",
                "pms.budget.view",
                "pms.budget.manage",
            ),
            roles=("staff",),
        )
        budget_payload = {
            "filing_fees": "15000.00",
            "attorney_fees": "30000.00",
            "administrative_costs": "5000.00",
        }
        budget_res = c_admin.post(
            f"/api/v1/pms/applications/{app.id}/budget",
            data=budget_payload,
            format="json",
        )
        assert budget_res.status_code == status.HTTP_200_OK, budget_res.data

        # 6. Director approves budget
        c_director = _make_client(
            stub_iam,
            user_id=9001,
            permissions=("pms.application.view", "pms.budget.approve"),
            roles=("Director",),
        )
        decide_res = c_director.post(
            f"/api/v1/pms/applications/{app.id}/budget/decide",
            data={"decision": "approve", "justification": "Budget approved within limits."},
            format="json",
        )
        assert decide_res.status_code == status.HTTP_200_OK, decide_res.data


class TestDocumentsAndAuditApi:
    def test_document_upload_and_download(self, stub_iam):
        app = PatentApplication.objects.create(
            user_id=1001,
            title="Solar Cell Coating",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="Energy",
            status="needs_revision",
        )

        client = _make_client(
            stub_iam,
            user_id=1001,
            permissions=("pms.application.view", "pms.document.view", "pms.document.create"),
        )

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Solar Cell) >>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        uploaded_file = SimpleUploadedFile(
            "solar_spec_v1.pdf",
            pdf_bytes,
            content_type="application/pdf",
        )

        # 1. Upload document
        upload_res = client.post(
            f"/api/v1/pms/applications/{app.id}/documents",
            data={
                "file": uploaded_file,
                "document_type": "specification",
                "sensitivity": "confidential",
            },
            format="multipart",
        )
        assert upload_res.status_code == status.HTTP_201_CREATED, upload_res.data
        doc_id = upload_res.json()["id"]

        # 2. Download document
        download_res = client.get(f"/api/v1/pms/documents/{doc_id}/download")
        assert download_res.status_code == status.HTTP_200_OK
        assert b"%PDF-1.4" in b"".join(download_res.streaming_content)

        # 3. Check Audit Logs timeline
        history_res = client.get(f"/api/v1/pms/applications/{app.id}/history")
        assert history_res.status_code == status.HTTP_200_OK
        logs = history_res.json()["results"]
        assert len(logs) >= 1
        assert any(log["action_type"] == "upload_document" for log in logs)


class TestProsecutionAndPostGrantApi:
    def test_filing_and_office_actions_api(self, stub_iam):
        # 1. Prepare ready-to-file application
        from modules.pms.domain.constants import STATUS_ATTORNEY_ASSIGNED
        from modules.pms.models import (
            AttorneyAssignment,
            PatentabilityAssessment,
            PatentBudget,
        )

        app = PatentApplication.objects.create(
            user_id=1001,
            title="Hybrid Electrolyzer",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="Energy",
            status=STATUS_ATTORNEY_ASSIGNED,
        )
        AttorneyAssignment.objects.create(
            application=app,
            attorney_user_id=7001,
            assigned_by_user_id=8888,
            status="accepted",
        )
        PatentBudget.objects.create(
            application=app,
            filing_fees=10000,
            attorney_fees=20000,
            administrative_costs=5000,
            total_cost=35000,
            status="approved",
        )
        PatentabilityAssessment.objects.create(
            application=app,
            attorney_user_id=7001,
            recommendation="file_patent",
            novelty_analysis="Novel cathode design.",
            inventive_step_analysis="Inventive step in catalyst loading.",
            utility_analysis="High efficiency.",
            prior_art_summary="None.",
            opinion_text="Patentable.",
        )

        c_attorney = _make_client(
            stub_iam,
            user_id=7001,
            permissions=(
                "pms.application.view",
                "pms.filing.create",
                "pms.office_action.view",
                "pms.office_action.create",
                "pms.office_action.update",
            ),
            roles=("staff",),
        )

        # 2. Record external patent filing
        filing_payload = {
            "jurisdiction": "IN",
            "filing_number": "202611009999",
            "filing_date": "2026-11-02",
            "patent_office": "Indian Patent Office, New Delhi",
            "confirmation_details": "CBR received. Priority date locked.",
        }
        filing_res = c_attorney.post(
            f"/api/v1/pms/applications/{app.id}/filing",
            data=filing_payload,
            format="json",
        )
        assert filing_res.status_code == status.HTTP_201_CREATED, filing_res.data
        app.refresh_from_db()
        assert app.status == "filed"

        # 3. Record First Examination Report (Office Action)
        oa_payload = {
            "action_number": "FER/2026/001",
            "issue_date": "2026-11-02",
            "response_deadline": "2027-05-02",
            "action_type": "FER",
            "description": "Objections raised under Section 3(d).",
        }
        oa_res = c_attorney.post(
            f"/api/v1/pms/applications/{app.id}/office-actions",
            data=oa_payload,
            format="json",
        )
        assert oa_res.status_code == status.HTTP_201_CREATED, oa_res.data
        oa_id = oa_res.json()["id"]

        # 4. Prepare draft response requiring applicant review
        resp_payload = {
            "response_text": "Amended Claim 1 to emphasize synergistic catalyst activity.",
            "requires_applicant_review": True,
        }
        resp_res = c_attorney.post(
            f"/api/v1/pms/office-actions/{oa_id}/response",
            data=resp_payload,
            format="json",
        )
        assert resp_res.status_code == status.HTTP_200_OK, resp_res.data
        resp_id = resp_res.json()["id"]

        # 5. Applicant reviews and approves response
        c_applicant = _make_client(
            stub_iam,
            user_id=1001,
            permissions=("pms.application.view", "pms.office_action.approve"),
        )
        appr_res = c_applicant.post(
            f"/api/v1/pms/office-actions/responses/{resp_id}/approve",
            format="json",
        )
        assert appr_res.status_code == status.HTTP_200_OK, appr_res.data

        # 6. Attorney submits response
        _make_client(
            stub_iam,
            user_id=7001,
            permissions=(
                "pms.application.view",
                "pms.office_action.view",
                "pms.office_action.update",
            ),
            roles=("staff",),
        )
        submit_res = c_attorney.post(
            f"/api/v1/pms/office-actions/responses/{resp_id}/submit",
            data={"submission_details": "Submitted electronically via IPO portal."},
            format="json",
        )
        assert submit_res.status_code == status.HTTP_200_OK, submit_res.data
        app.refresh_from_db()
        assert app.status == "response_submitted"

    def test_post_grant_maintenance_and_licensing_api(self, stub_iam):
        app = PatentApplication.objects.create(
            user_id=1001,
            title="Advanced Battery Separator",
            abstract="Abs",
            description="Desc",
            claims="Claims",
            domain="Energy",
            status="filed",
        )

        c_admin = _make_client(
            stub_iam,
            user_id=8888,
            permissions=(
                "pms.application.view",
                "pms.maintenance.view",
                "pms.maintenance.manage",
                "pms.licensing.view",
                "pms.licensing.manage",
            ),
            roles=("staff",),
        )

        # 1. Initialize Post-Grant Patent
        grant_payload = {
            "grant_number": "IN-450912",
            "grant_date": "2026-11-02",
            "patent_document_url": "https://ipo.gov.in/patents/450912.pdf",
        }
        grant_res = c_admin.post(
            f"/api/v1/pms/applications/{app.id}/grant",
            data=grant_payload,
            format="json",
        )
        assert grant_res.status_code == status.HTTP_201_CREATED, grant_res.data
        app.refresh_from_db()
        assert app.status == "granted"

        # 2. List Maintenance Schedules
        maint_res = c_admin.get("/api/v1/pms/maintenance")
        assert maint_res.status_code == status.HTTP_200_OK
        schedules = maint_res.json()["results"]
        assert len(schedules) == 18  # Years 3 through 20
        sched_id = schedules[0]["id"]

        # 3. Request Renewal Decision
        req_res = c_admin.post(
            f"/api/v1/pms/maintenance/{sched_id}/request-decision",
            format="json",
        )
        assert req_res.status_code == status.HTTP_200_OK

        # 4. Director decides renewal
        c_director = _make_client(
            stub_iam,
            user_id=9001,
            permissions=("pms.application.view", "pms.maintenance.review"),
            roles=("Director",),
        )
        decide_res = c_director.post(
            f"/api/v1/pms/maintenance/{sched_id}/decide",
            data={"decision": "renew", "justification": "Commercially active patent license."},
            format="json",
        )
        assert decide_res.status_code == status.HTTP_200_OK

        # 5. PCC Admin records payment
        _make_client(
            stub_iam,
            user_id=8888,
            permissions=("pms.application.view", "pms.maintenance.manage"),
            roles=("staff",),
        )
        pay_res = c_admin.post(
            f"/api/v1/pms/maintenance/{sched_id}/pay",
            data={"paid_amount": "800.00", "payment_reference": "TXN-RENEW-2026-001"},
            format="json",
        )
        assert pay_res.status_code == status.HTTP_200_OK

    def test_appeals_prior_art_and_reports_api(self, stub_iam):
        # 1. Prior Art Search Record
        c_admin = _make_client(
            stub_iam,
            user_id=8888,
            permissions=(
                "pms.application.view",
                "pms.prior_art.view",
                "pms.prior_art.manage",
                "pms.report.view",
                "pms.audit.view",
            ),
            roles=("staff",),
        )
        pa_payload = {
            "keywords": "solid state electrolyte dendrite suppression",
            "databases_searched": "Google Patents, Espacenet, IEEE",
            "results_summary": "Identified 3 relevant US patents on garnet electrolytes.",
        }
        pa_res = c_admin.post("/api/v1/pms/prior-art", data=pa_payload, format="json")
        assert pa_res.status_code == status.HTTP_201_CREATED, pa_res.data
        pa_id = pa_res.json()["id"]
        assert pa_id > 0

        # 2. Portfolio Summary Report
        report_res = c_admin.get("/api/v1/pms/reports/summary")
        assert report_res.status_code == status.HTTP_200_OK
        data = report_res.json()
        assert "total_applications" in data
        assert "granted_count" in data

        # 3. Compliance Audit Log List
        audit_res = c_admin.get("/api/v1/pms/audit-logs")
        assert audit_res.status_code == status.HTTP_200_OK
        assert "results" in audit_res.json()
