"""Tests for patents selectors and scoping (Step 4.3)."""
from __future__ import annotations

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import NotFoundError
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    AppealRecord,
    ApplicationDocument,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
    ReviewDecision,
    TechnologyTransferRecord,
)
from modules.patents.selectors import (
    appeals_for,
    applications_for,
    applications_in_assessment,
    applications_pending_attorney_response,
    applications_pending_director_review,
    attorney_panel_for,
    budget_entries_for,
    co_inventors_for,
    documents_for,
    get_application,
    get_application_or_404,
    get_document_or_404,
    get_office_action_or_404,
    granted_applications,
    has_pms_access,
    is_applicant,
    is_attorney,
    is_director,
    is_pcc_admin,
    office_actions_for,
    policies_for,
    review_decisions_for,
    tech_transfers_for,
    visible_applications,
)

pytestmark = pytest.mark.django_db


# -- Actor Helpers -------------------------------------------------------------

def applicant_actor(user_id=101):
    return make_principal(
        user_id=user_id,
        kind="student",
        roles=("student",),
        active_role="student",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE),
    )


def director_actor(user_id=201):
    return make_principal(
        user_id=user_id,
        kind="faculty",
        roles=("Director",),
        active_role="Director",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_REVIEW, p.P_BUDGET_APPROVE),
    )


def attorney_actor(user_id=301):
    return make_principal(
        user_id=user_id,
        kind="external",
        roles=("attorney",),
        active_role="attorney",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW, p.P_ASSESSMENT_PERFORM, p.P_FILING_RECORD),
    )


def pcc_admin_actor(user_id=401):
    return make_principal(
        user_id=user_id,
        kind="staff",
        roles=("pcc_admin",),
        active_role="pcc_admin",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_ASSIGN_DIRECTOR, p.P_AUDIT_VIEW),
    )


def outsider_actor(user_id=999):
    return make_principal(
        user_id=user_id,
        kind="student",
        roles=("other_role",),
        active_role="other_role",
        modules=("other_module",),
        permissions=(),
    )


# -- Test Role Predicates ------------------------------------------------------

def test_role_predicates():
    app = applicant_actor(1)
    dir_act = director_actor(2)
    att = attorney_actor(3)
    adm = pcc_admin_actor(4)
    out = outsider_actor(5)

    assert is_applicant(app) is True
    assert is_director(dir_act) is True
    assert is_attorney(att) is True
    assert is_pcc_admin(adm) is True

    assert has_pms_access(app) is True
    assert has_pms_access(dir_act) is True
    assert has_pms_access(att) is True
    assert has_pms_access(adm) is True
    assert has_pms_access(out) is False
    assert has_pms_access(None) is False


# -- Test Applications Scoping -------------------------------------------------

def test_applicant_scoping():
    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0001",
        title="App 1",
        abstract="Abstract 1",
        description="Desc 1",
        claims="Claims 1",
        status=sm.SUBMITTED,
    )
    app2 = PatentApplication.objects.create(
        user_id=102,
        application_number="PMS-2026-0002",
        title="App 2",
        abstract="Abstract 2",
        description="Desc 2",
        claims="Claims 2",
        status=sm.SUBMITTED,
    )
    CoInventor.objects.create(
        application=app1,
        user_id=103,
        name="Co-Inventor 1",
        email="co1@example.com",
        share_percentage="30.00",
    )

    actor1 = applicant_actor(101)
    actor2 = applicant_actor(102)
    actor3_coinventor = applicant_actor(103)

    # Actor 1 sees only App 1
    qs1 = applications_for(actor1)
    assert app1 in qs1
    assert app2 not in qs1

    # Actor 2 sees only App 2
    qs2 = applications_for(actor2)
    assert app2 in qs2
    assert app1 not in qs2

    # Actor 3 (co-inventor on App 1) sees App 1
    qs3 = applications_for(actor3_coinventor)
    assert app1 in qs3
    assert app2 not in qs3

    # get_application_or_404 returns app if in scope
    assert get_application_or_404(actor1, app1.id) == app1
    assert get_application(actor1, app1.id) == app1

    # Out of scope raises NotFoundError (404), never 403
    with pytest.raises(NotFoundError):
        get_application_or_404(actor1, app2.id)
    assert get_application(actor1, app2.id) is None


def test_director_scoping():
    dir1 = director_actor(201)
    dir2 = director_actor(202)

    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0011",
        title="App 1",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_director_id=201,
        status=sm.UNDER_REVIEW,
    )
    app2 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0012",
        title="App 2",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_director_id=202,
        status=sm.UNDER_REVIEW,
    )
    # Director 201 authored their own app, reviewed by Director 202
    app3_own = PatentApplication.objects.create(
        user_id=201,
        application_number="PMS-2026-0013",
        title="Director Own App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_director_id=202,
        status=sm.UNDER_REVIEW,
    )

    qs_dir1 = applications_for(dir1)
    assert app1 in qs_dir1
    assert app2 not in qs_dir1
    assert app3_own in qs_dir1  # Can view own application

    qs_dir2 = applications_for(dir2)
    assert app1 not in qs_dir2
    assert app2 in qs_dir2
    assert app3_own in qs_dir2  # Assigned to dir2


def test_attorney_scoping():
    att1 = attorney_actor(301)
    att2 = attorney_actor(302)

    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0021",
        title="App 1",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_attorney_id=301,
        status=sm.ASSESSMENT_IN_PROGRESS,
    )
    app2 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0022",
        title="App 2",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_attorney_id=302,
        status=sm.ASSESSMENT_IN_PROGRESS,
    )

    assert app1 in applications_for(att1)
    assert app2 not in applications_for(att1)

    assert app1 not in applications_for(att2)
    assert app2 in applications_for(att2)

    with pytest.raises(NotFoundError):
        get_application_or_404(att1, app2.id)


def test_pcc_admin_sees_everything():
    admin = pcc_admin_actor(401)

    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0031",
        title="App 1",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )
    app2 = PatentApplication.objects.create(
        user_id=102,
        application_number="PMS-2026-0032",
        title="App 2",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )

    qs = applications_for(admin)
    assert app1 in qs
    assert app2 in qs
    assert get_application_or_404(admin, app1.id) == app1
    assert get_application_or_404(admin, app2.id) == app2


def test_unauthenticated_or_outsider_isolation():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0041",
        title="App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )

    assert applications_for(None).count() == 0
    assert applications_for(outsider_actor(999)).count() == 0

    with pytest.raises(NotFoundError):
        get_application_or_404(outsider_actor(999), app.id)


# -- Test Subordinate Entities Scoping -----------------------------------------

def test_documents_scoping():
    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0051",
        title="App 1",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )
    app2 = PatentApplication.objects.create(
        user_id=102,
        application_number="PMS-2026-0052",
        title="App 2",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )
    doc1 = ApplicationDocument.objects.create(
        application=app1,
        document_type="specification",
        file_name="spec.pdf",
        file_format="pdf",
        file_size_bytes=1024,
        storage_path="/var/docs/spec1.pdf",
        uploaded_by_user_id=101,
    )
    doc2 = ApplicationDocument.objects.create(
        application=app2,
        document_type="specification",
        file_name="spec.pdf",
        file_format="pdf",
        file_size_bytes=1024,
        storage_path="/var/docs/spec2.pdf",
        uploaded_by_user_id=102,
    )

    actor1 = applicant_actor(101)
    assert doc1 in documents_for(actor1)
    assert doc2 not in documents_for(actor1)
    assert get_document_or_404(actor1, doc1.id) == doc1

    with pytest.raises(NotFoundError):
        get_document_or_404(actor1, doc2.id)


def test_subordinate_entities_scoping():
    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0061",
        title="App 1",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_director_id=201,
    )
    PatentApplication.objects.create(
        user_id=102,
        application_number="PMS-2026-0062",
        title="App 2",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_director_id=202,
    )

    co1 = CoInventor.objects.create(
        application=app1,
        user_id=103,
        name="Co 1",
        email="co1@ex.com",
        share_percentage="50.00",
    )
    rev1 = ReviewDecision.objects.create(
        application=app1,
        director_user_id=201,
        decision="REJECT",
        justification="Needs more prior art references to establish novelty under Section 3.",
    )
    appeal1 = AppealRecord.objects.create(
        application=app1,
        applicant_user_id=101,
        grounds="Prior art cited is non-analogous art.",
    )
    budget1 = PatentBudgetLedger.objects.create(
        application=app1,
        entry_type="APPROVAL",
        amount="25000.00",
        category="filing_fee",
        authorized_by_user_id=201,
    )
    oa1 = OfficeActionRecord.objects.create(
        application=app1,
        action_code="FER-1",
        issuing_authority="IPO Delhi",
        issued_date=timezone.now().date(),
        response_deadline=timezone.now().date(),
    )
    tech1 = TechnologyTransferRecord.objects.create(
        application=app1,
        applicant_user_id=101,
        request_type="licensing",
        partner_name="Acme Tech",
    )

    actor1 = applicant_actor(101)
    actor2 = applicant_actor(102)

    assert co1 in co_inventors_for(actor1)
    assert rev1 in review_decisions_for(actor1)
    assert appeal1 in appeals_for(actor1)
    assert budget1 in budget_entries_for(actor1)
    assert oa1 in office_actions_for(actor1)
    assert tech1 in tech_transfers_for(actor1)

    assert co1 not in co_inventors_for(actor2)
    assert rev1 not in review_decisions_for(actor2)
    assert appeal1 not in appeals_for(actor2)
    assert budget1 not in budget_entries_for(actor2)
    assert oa1 not in office_actions_for(actor2)
    assert tech1 not in tech_transfers_for(actor2)

    assert get_office_action_or_404(actor1, oa1.id) == oa1
    with pytest.raises(NotFoundError):
        get_office_action_or_404(actor2, oa1.id)


def test_attorney_panel_and_policy_scoping():
    p1 = AttorneyPanelMember.objects.create(
        user_id=301,
        firm_name="Firm Alpha",
        is_approved_panel=True,
    )
    p2 = AttorneyPanelMember.objects.create(
        user_id=302,
        firm_name="Firm Beta",
        is_approved_panel=False,
    )

    pol_active = PatentPolicy.objects.create(is_active=True)
    pol_inactive = PatentPolicy.objects.create(is_active=False)

    admin = pcc_admin_actor(401)
    att1 = attorney_actor(301)
    app = applicant_actor(101)

    # Panel scoping
    assert p1 in attorney_panel_for(admin)
    assert p2 in attorney_panel_for(admin)

    assert p1 in attorney_panel_for(att1)
    assert p2 not in attorney_panel_for(att1)

    assert p1 in attorney_panel_for(app)
    assert p2 not in attorney_panel_for(app)

    # Policy scoping
    assert pol_active in policies_for(admin)
    assert pol_inactive in policies_for(admin)

    assert pol_active in policies_for(app)
    assert pol_inactive not in policies_for(app)


def test_workflow_query_helpers():
    dir1 = director_actor(201)
    att1 = attorney_actor(301)

    app_rev = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0071",
        title="App Rev",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_director_id=201,
        status=sm.UNDER_REVIEW,
    )
    app_off = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0072",
        title="App Off",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_attorney_id=301,
        status=sm.ASSIGNMENT_OFFERED,
    )
    app_ass = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0073",
        title="App Ass",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_attorney_id=301,
        status=sm.ASSESSMENT_IN_PROGRESS,
    )
    app_grt = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0074",
        title="App Grt",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.GRANTED,
    )

    assert app_rev in applications_pending_director_review(dir1)
    assert app_off in applications_pending_attorney_response(att1)
    assert app_ass in applications_in_assessment(att1)
    assert app_grt in granted_applications(applicant_actor(101))
    assert visible_applications(dir1).count() >= 1
