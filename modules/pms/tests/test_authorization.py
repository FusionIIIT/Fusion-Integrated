"""Role-based authorization and security isolation tests for PMS.

Maps to:
- CFR-PMS-025 (Role Eligibility for PMS Access)
- CFR-PMS-026 (Lifecycle Authorization Gates)
- CFR-PMS-027 (Confidential Patent Information Access)
- BR-PMS-003, BR-PMS-005, BR-PMS-006, BR-PMS-126, BR-PMS-130
"""


import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import AttorneyAssignment, PmsRoleAssignment
from modules.pms.services import submit_application

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=1001, roles=("student",), permissions=(), modules=("pms",)):
    session = make_session(
        user_id=user_id,
        roles=roles,
        active_role=roles[0] if roles else None,
        permissions=permissions,
        modules=modules,
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_unauthenticated_request_denied():
    """Unauthenticated request must be denied (401 or 403)."""
    client = APIClient()
    response = client.get("/api/v1/pms/applications/")
    assert response.status_code in (401, 403)


def test_unassigned_pms_module_denied(stub_iam):
    """CFR-PMS-025, BR-PMS-126: User without PMS module grant cannot access PMS endpoints."""
    # User has modules=("placement_cell",), NOT "pms"
    client = _auth_client(stub_iam, user_id=1001, modules=("placement_cell",))
    response = client.get("/api/v1/pms/applications/")
    assert response.status_code == 403


def test_applicant_scoping_isolation(stub_iam):
    """BR-PMS-003, BR-PMS-130: Applicant sees only their own applications or co-invented applications."""
    app_user1 = submit_application(
        applicant_user_id=1001,
        title="User 1 Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app_user2 = submit_application(
        applicant_user_id=2001,
        title="User 2 Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )

    client1 = _auth_client(
        stub_iam, user_id=1001, permissions=("pms.application.view_self", "pms.application.create")
    )

    # List only returns app_user1
    res = client1.get("/api/v1/pms/applications/")
    assert res.status_code == 200
    app_ids = [a["id"] for a in res.json()]
    assert app_user1.id in app_ids
    assert app_user2.id not in app_ids

    # Detail access for foreign application yields 404
    res_foreign = client1.get(f"/api/v1/pms/applications/{app_user2.id}/")
    assert res_foreign.status_code == 404


def test_coinventor_can_view_application(stub_iam):
    """CFR-PMS-016: Co-inventor has read access to the application."""
    app = submit_application(
        applicant_user_id=1001,
        title="Shared Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 1002,
                "name": "Co-Inventor",
                "email": "co@test.com",
                "ownership_percentage": "40.00",
            },
            {
                "user_id": 1001,
                "name": "Primary",
                "email": "p@test.com",
                "ownership_percentage": "60.00",
            },
        ],
    )

    client_coinv = _auth_client(stub_iam, user_id=1002, permissions=("pms.application.view_self",))
    res = client_coinv.get(f"/api/v1/pms/applications/{app.id}/")
    assert res.status_code == 200
    assert res.json()["title"] == "Shared Patent"


def test_director_scope_is_domain_or_assignment_only(stub_iam):
    assigned = submit_application(
        applicant_user_id=1001,
        title="Assigned",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Physics",
    )
    assigned.assigned_director_user_id = 2001
    assigned.save(update_fields=["assigned_director_user_id", "updated_at"])
    in_domain = submit_application(
        applicant_user_id=1002,
        title="In domain",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Physics",
    )
    out_of_scope = submit_application(
        applicant_user_id=1003,
        title="Outside scope",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Chemistry",
    )
    PmsRoleAssignment.objects.create(user_id=2001, role="Director", domain="Physics")

    client = _auth_client(
        stub_iam,
        user_id=2001,
        roles=("director",),
        permissions=("pms.application.view", "pms.application.review"),
    )
    response = client.get("/api/v1/pms/applications/")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert {assigned.id, in_domain.id} <= ids
    assert out_of_scope.id not in ids


def test_attorney_scope_excludes_declined_inactive_assignment(stub_iam):
    assigned = submit_application(
        applicant_user_id=1001,
        title="Active assignment",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Physics",
    )
    declined = submit_application(
        applicant_user_id=1002,
        title="Declined assignment",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Physics",
    )
    AttorneyAssignment.objects.create(
        application=assigned,
        attorney_user_id=5001,
        assigned_by_user_id=9001,
        status="accepted",
        is_active=True,
    )
    AttorneyAssignment.objects.create(
        application=declined,
        attorney_user_id=5001,
        assigned_by_user_id=9001,
        status="declined",
        is_active=True,
    )

    client = _auth_client(
        stub_iam,
        user_id=5001,
        roles=("attorney",),
        permissions=("pms.application.view", "pms.patentability.assess"),
    )
    response = client.get("/api/v1/pms/applications/")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert assigned.id in ids
    assert declined.id not in ids


def test_nested_endpoint_hides_foreign_application_records(stub_iam):
    app = submit_application(
        applicant_user_id=2001,
        title="Private patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    coinventor = app.coinventors.create(
        user_id=2002,
        name="Co-inventor",
        email="co@example.test",
        ownership_percentage="100.00",
    )
    client = _auth_client(
        stub_iam,
        user_id=1001,
        permissions=("pms.coinventor.manage",),
    )
    response = client.post(
        f"/api/v1/pms/coinventors/{coinventor.id}/consent/",
        {"consent_given": True, "agreement_signed": True},
    )
    assert response.status_code == 404
    coinventor.refresh_from_db()
    assert not coinventor.agreement_signed


def test_applicant_cannot_revise_another_applicants_application(stub_iam):
    """CFR-PMS-008: revise permission does not bypass application ownership."""
    app = submit_application(
        applicant_user_id=2001,
        title="Private Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    client = _auth_client(
        stub_iam,
        user_id=1001,
        permissions=("pms.application.revise", "pms.application.view_self"),
    )
    response = client.post(
        f"/api/v1/pms/applications/{app.id}/revise/",
        {"feedback_response": "Updated the requested technical details."},
    )

    # 403, not 400: the caller holds pms.application.revise but is not this
    # application's applicant — an authorization refusal. That matches the
    # platform convention (PermissionDeniedError = 403) and the placement
    # precedent that maps actor-not-allowed to 403 (CFR-PMS-008, BR-PMS-126).
    assert response.status_code == 403
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value


def test_director_cannot_submit_review_without_permission(stub_iam):
    """CFR-PMS-007, BR-PMS-029: Only users with pms.application.review can submit reviews."""
    app = submit_application(
        applicant_user_id=1001,
        title="Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Student attempts review
    client = _auth_client(stub_iam, user_id=1001, permissions=("pms.application.view_self",))
    res = client.post(
        f"/api/v1/pms/applications/{app.id}/review/",
        {"decision": "Approve", "justification": "A" * 50},
    )
    assert res.status_code == 403


def test_attorney_endpoint_authorization(stub_iam):
    """CFR-PMS-012: Only users with pms.filing.record can record external filing."""
    app = submit_application(
        applicant_user_id=1001,
        title="Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Non-attorney tries to record filing
    client = _auth_client(stub_iam, user_id=1001, permissions=("pms.application.view_self",))
    res = client.post(
        f"/api/v1/pms/applications/{app.id}/filing/",
        {
            "external_filing_id": "IPO/123",
            "external_filing_date": "2026-11-01",
            "filing_confirmation": "Confirmed",
        },
    )
    assert res.status_code == 403


def test_pcc_admin_exclusive_assign_attorney_permission(stub_iam):
    """BR-PMS-040: Only PCC_ADMIN (pms.attorney.assign) may assign an Attorney."""
    app = submit_application(
        applicant_user_id=1001,
        title="Patent",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Director tries to assign attorney
    client = _auth_client(
        stub_iam,
        user_id=2001,
        roles=("director",),
        permissions=("pms.application.view", "pms.application.review"),
    )
    res = client.post(
        f"/api/v1/pms/applications/{app.id}/assign-attorney/", {"attorney_user_id": 5001}
    )
    assert res.status_code == 403


def test_non_owner_withdraw_is_403(stub_iam):
    """CFR-PMS-015, BR-PMS-126: an ownership refusal on another lifecycle action
    is also an authorization refusal, so the domain-to-HTTP mapping is general
    and not special-cased for revise."""
    app = submit_application(
        applicant_user_id=2001,
        title="Not yours",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    client = _auth_client(
        stub_iam, user_id=1001, permissions=("pms.application.withdraw",)
    )
    response = client.post(
        f"/api/v1/pms/applications/{app.id}/withdraw/", {"reason": "Not my application"}
    )
    assert response.status_code == 403
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.SUBMITTED.value
