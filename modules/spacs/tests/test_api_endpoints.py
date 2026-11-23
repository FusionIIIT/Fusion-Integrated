"""Comprehensive API endpoint test suite for SPACS."""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import (
    SpacsApplication,
    SpacsAwardCandidate,
    SpacsAwardCycle,
    SpacsTask,
)
from modules.spacs.services import audit as audit_svc
from modules.spacs.services import awards as award_svc
from modules.spacs.services import catalogue as cat_svc

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id=101, role="student", permissions=(), modules=("spacs",)):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="student" if role == "student" else "staff",
            roles=(role,),
            active_role=role,
            permissions=permissions,
            modules=modules,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_scheme_and_cycle_endpoints(stub_iam):
    # Create scheme as convener
    c_conv = _client(
        stub_iam,
        user_id=1,
        role="spacs_convener",
        permissions=(
            "spacs.scheme.view",
            "spacs.scheme.create",
            "spacs.scheme.update",
            "spacs.cycle.view",
            "spacs.cycle.create",
            "spacs.cycle.publish",
        ),
    )
    res = c_conv.post(
        "/api/v1/spacs/schemes",
        {
            "scheme_code": "SCH-API-01",
            "name": "API Merit Scheme",
            "scheme_type": "scholarship",
            "min_cpi": "7.5",
            "max_family_income": "600000",
            "required_documents": ["income_cert"],
            "academic_cycle": "2026-27",
            "renewal_allowed": True,
        },
        format="json",
    )
    assert res.status_code == 201
    scheme_id = res.data["id"]

    # Read scheme list and detail
    c_stud = _client(
        stub_iam,
        user_id=42,
        role="student",
        permissions=("spacs.scheme.view", "spacs.cycle.view"),
    )
    res_list = c_stud.get("/api/v1/spacs/schemes")
    assert res_list.status_code == 200

    res_det = c_stud.get(f"/api/v1/spacs/schemes/{scheme_id}")
    assert res_det.status_code == 200
    assert res_det.data["scheme_code"] == "SCH-API-01"

    # Patch scheme as convener
    c_conv = _client(
        stub_iam,
        user_id=1,
        role="spacs_convener",
        permissions=(
            "spacs.scheme.view",
            "spacs.scheme.create",
            "spacs.scheme.update",
            "spacs.cycle.view",
            "spacs.cycle.create",
            "spacs.cycle.publish",
        ),
    )
    res_patch = c_conv.patch(
        f"/api/v1/spacs/schemes/{scheme_id}",
        {"name": "Patched Scheme Name"},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.data["name"] == "Patched Scheme Name"

    # Create cycle
    now = timezone.now()
    res_cyc = c_conv.post(
        "/api/v1/spacs/cycles",
        {
            "scheme_code": "SCH-API-01",
            "academic_cycle": "2026-27",
            "application_window_start": (now - timedelta(days=1)).isoformat(),
            "application_window_end": (now + timedelta(days=30)).isoformat(),
        },
        format="json",
    )
    assert res_cyc.status_code == 201
    cycle_id = res_cyc.data["id"]

    # Update cycle to ready_for_publication with institutional evidence
    SpacsAwardCycle.objects.filter(id=cycle_id).update(
        state="ready_for_publication", approval_evidence="SENATE-2026"
    )
    res_cyc_pub = c_conv.post(f"/api/v1/spacs/cycles/{cycle_id}/publish")
    assert res_cyc_pub.status_code == 200


def test_application_lifecycle_endpoints(stub_iam):
    now = timezone.now()
    entry = cat_svc.create_catalogue_entry(
        scheme_code="SCH-API-APP",
        name="Application API Scheme",
        scheme_type="scholarship",
        min_cpi=7.0,
        application_window_start=now - timedelta(days=2),
        application_window_end=now + timedelta(days=30),
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version("SCH-API-APP", "POL-01", date.today(), 1)

    c_stud = _client(
        stub_iam,
        user_id=55,
        role="student",
        permissions=(
            "spacs.scheme.view",
            "spacs.application.view",
            "spacs.application.create",
            "spacs.application.update",
        ),
    )

    # Submit application
    res_sub = c_stud.post(
        "/api/v1/spacs/applications",
        {
            "scheme_code": "SCH-API-APP",
            "academic_cycle": "2026-27",
            "cpi": 8.0,
            "family_income": 300000.0,
        },
        format="json",
    )
    assert res_sub.status_code == 201
    app_id = res_sub.data["id"]
    app_code = res_sub.data["application_id"]

    # Get applications list
    res_apps = c_stud.get("/api/v1/spacs/applications")
    assert res_apps.status_code == 200
    assert len(res_apps.data) >= 1

    # Get application detail
    res_det = c_stud.get(f"/api/v1/spacs/applications/{app_id}")
    assert res_det.status_code == 200

    # Assistant verification
    c_asst = _client(
        stub_iam,
        user_id=10,
        role="spacs_assistant",
        permissions=("spacs.application.view", "spacs.application.review"),
    )
    res_q = c_asst.get("/api/v1/spacs/verifications")
    assert res_q.status_code == 200

    res_v_action = c_asst.post(
        f"/api/v1/spacs/verifications/{app_id}/action",
        {"action": "verify", "notes": "Documents verified"},
        format="json",
    )
    assert res_v_action.status_code == 200
    assert res_v_action.data["state"] == "verified"

    # Convener decision
    c_conv = _client(
        stub_iam,
        user_id=1,
        role="spacs_convener",
        permissions=(
            "spacs.application.view",
            "spacs.application.review",
            "spacs.application.approve",
        ),
    )
    res_dec = c_conv.post(
        "/api/v1/spacs/decisions/action",
        {"application_id": app_code, "outcome": "approved", "reason": "Merit"},
        format="json",
    )
    assert res_dec.status_code == 200
    assert res_dec.data["state"] == "approved"

    # Student withdraw on draft app
    app_draft = SpacsApplication.objects.create(
        application_id="DRAFT-WITHDRAW-01",
        catalogue_entry=entry,
        applicant_user_id=55,
        academic_cycle="2026-27",
        state="submitted",
    )
    c_stud = _client(
        stub_iam,
        user_id=55,
        role="student",
        permissions=(
            "spacs.scheme.view",
            "spacs.application.view",
            "spacs.application.create",
            "spacs.application.update",
        ),
    )
    res_wd = c_stud.post(f"/api/v1/spacs/applications/{app_draft.id}/withdraw")
    assert res_wd.status_code == 200
    assert res_wd.data["state"] == "withdrawn"


def test_awards_and_audit_endpoints(stub_iam):
    entry = cat_svc.create_catalogue_entry(
        scheme_code="AWARD-API-01",
        name="Medal API Scheme",
        scheme_type="award",
        created_by_user_id=1,
    )
    cycle = SpacsAwardCycle.objects.create(
        catalogue_entry=entry,
        academic_cycle="2026-27",
        state="ready_for_publication",
        approval_evidence="SENATE-APR-2026",
    )
    SpacsAwardCandidate.objects.create(
        award_cycle=cycle,
        student_user_id=88,
        cpi=9.8,
        academic_standing="good",
        shortlisted=True,
        committee_recommendation="winner",
    )

    c_conv = _client(
        stub_iam,
        user_id=1,
        role="spacs_convener",
        permissions=(
            "spacs.award.view",
            "spacs.award.create",
            "spacs.award.publish",
            "spacs.award.export",
            "spacs.application.review",
            "spacs.audit.view",
        ),
    )

    # Awards list
    res_aw = c_conv.get("/api/v1/spacs/awards")
    assert res_aw.status_code == 200
    assert len(res_aw.data) >= 1

    # Awards export
    res_exp = c_conv.get("/api/v1/spacs/awards/export")
    assert res_exp.status_code == 200

    # Awards publish
    res_pub = c_conv.post(
        "/api/v1/spacs/awards/publish",
        {"cycle_id": cycle.id, "approval_evidence": "SENATE-APR-2026"},
        format="json",
    )
    assert res_pub.status_code == 200

    # Tasks list
    SpacsTask.objects.create(
        task_type="verification",
        entity_type="application",
        entity_id="SPACS-TASK-01",
        assigned_role="spacs_assistant",
    )
    res_t = c_conv.get("/api/v1/spacs/tasks")
    assert res_t.status_code == 200

    # Audit trail list
    audit_svc.log_action("api_test", "application", "SPACS-AUD-01", 1)
    res_aud = c_conv.get("/api/v1/spacs/audit")
    assert res_aud.status_code == 200


def test_renewal_and_defect_endpoints(stub_iam):
    from modules.spacs.services import renewals as rnw_svc
    from modules.spacs.services import verification as ver_svc

    now = timezone.now()
    entry = cat_svc.create_catalogue_entry(
        scheme_code="SCH-API-RNW",
        name="Renewal API Scheme",
        scheme_type="scholarship",
        min_cpi=7.0,
        renewal_allowed=True,
        application_window_start=now - timedelta(days=2),
        application_window_end=now + timedelta(days=30),
        renewal_window_start=now - timedelta(days=2),
        renewal_window_end=now + timedelta(days=30),
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version("SCH-API-RNW", "POL-RNW-01", date.today(), 1)

    parent_app = SpacsApplication.objects.create(
        application_id="PARENT-APP-99",
        catalogue_entry=entry,
        applicant_user_id=60,
        academic_cycle="2025-26",
        state="approved",
    )

    c_stud = _client(
        stub_iam,
        user_id=60,
        role="student",
        permissions=(
            "spacs.scheme.view",
            "spacs.application.view",
            "spacs.application.create",
            "spacs.application.update",
        ),
    )
    res_rnw = c_stud.post(
        "/api/v1/spacs/renewals",
        {
            "parent_application_id": parent_app.application_id,
            "academic_cycle": "2026-27",
            "cpi": 8.5,
            "family_income": 350000.0,
        },
        format="json",
    )
    assert res_rnw.status_code == 201
    rnw_id = res_rnw.data["id"]

    c_asst = _client(
        stub_iam,
        user_id=10,
        role="spacs_assistant",
        permissions=("spacs.application.view", "spacs.application.review"),
    )
    res_def = c_asst.post(
        f"/api/v1/spacs/verifications/{rnw_id}/action",
        {"action": "defect", "notes": "Need current grade sheet"},
        format="json",
    )
    assert res_def.status_code == 200

    concern_app = SpacsApplication.objects.create(
        application_id="CONCERN-APP-01",
        catalogue_entry=entry,
        applicant_user_id=61,
        academic_cycle="2026-27",
        state="under_verification",
    )
    ver_svc.record_verification_concern(
        application_id=concern_app.application_id,
        assistant_user_id=10,
        user_roles=["spacs_assistant"],
        concern_notes="Suspicious signature",
    )
    concern_app.refresh_from_db()
    assert concern_app.state == "verification_concern"

    reminded = rnw_svc.send_renewal_reminders("SCH-API-RNW")
    assert 60 in reminded


def test_additional_views_coverage(stub_iam):
    c_conv = _client(
        stub_iam,
        user_id=1,
        role="spacs_convener",
        permissions=(
            "spacs.scheme.view",
            "spacs.scheme.create",
            "spacs.scheme.update",
            "spacs.application.view",
            "spacs.award.create",
            "spacs.award.export",
            "spacs.cycle.publish",
            "spacs.audit.view",
        ),
    )
    now = timezone.now()
    entry = cat_svc.create_catalogue_entry(
        scheme_code="SCH-ADD-VIEW",
        name="Additional View Scheme",
        scheme_type="award",
        application_window_start=now - timedelta(days=2),
        application_window_end=now + timedelta(days=20),
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version("SCH-ADD-VIEW", "POL-ADD", date.today(), 1)
    res = c_conv.get(f"/api/v1/spacs/schemes/{entry.id}")
    assert res.status_code == 200

    res_p = c_conv.patch(
        f"/api/v1/spacs/schemes/{entry.id}",
        {"description": "Updated scheme description"},
        format="json",
    )
    assert res_p.status_code == 200

    cycle = award_svc.open_award_cycle(
        scheme_code=entry.scheme_code,
        academic_cycle="2026-27",
        convener_user_id=1,
    )
    res_aw = c_conv.post(
        "/api/v1/spacs/awards",
        {
            "award_cycle": cycle.id,
            "student_user_id": 888,
            "cpi": 9.2,
            "academic_standing": "good",
        },
        format="json",
    )
    assert res_aw.status_code == 201

    res_aw_list = c_conv.get("/api/v1/spacs/awards")
    assert res_aw_list.status_code == 200

    res_exp = c_conv.get("/api/v1/spacs/awards/export")
    assert res_exp.status_code == 200

    res_rnw_get = c_conv.get("/api/v1/spacs/renewals")
    assert res_rnw_get.status_code == 200

    res_aud = c_conv.get("/api/v1/spacs/audit?entity_type=application")
    assert res_aud.status_code == 200

    c_stud = _client(
        stub_iam,
        user_id=60,
        role="student",
        permissions=("spacs.application.view",),
    )
    res_stud_rnw = c_stud.get("/api/v1/spacs/renewals")
    assert res_stud_rnw.status_code == 200

