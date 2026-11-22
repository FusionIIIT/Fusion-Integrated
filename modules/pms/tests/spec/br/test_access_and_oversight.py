"""Business Rule tests for access control, scoping, and role governance."""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from conftest import make_principal
from modules.pms.domain.errors import ConflictOfInterestError, NotPermittedError
from modules.pms.models import PatentApplication, PmsRoleAssignment
from modules.pms.selectors.applications import visible_applications
from modules.pms.services import assign_director, submit_application
from modules.pms.services.authorization import require_director_scope

pytestmark = pytest.mark.django_db


def test_br_tc_001_permitted_access_to_own_patent_application_report():
    """BR-TC-001 | BR-PMS-003: permitted access to own patent application report information."""
    app = submit_application(
        applicant_user_id=1001,
        title="Own Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Computing",
    )
    principal = make_principal(
        user_id=1001,
        permissions=("pms.application.view_self", "pms.report.view_self"),
        modules=("pms",),
        kind="faculty",
        roles=("Applicant",),
        active_role="Applicant",
    )
    visible_ids = list(visible_applications(principal).values_list("id", flat=True))
    assert app.id in visible_ids


def test_br_tc_002_prohibited_access_to_another_users_patent_application_report():
    """BR-TC-002 | BR-PMS-003: prohibited access to another user's patent application report information."""
    foreign_app = submit_application(
        applicant_user_id=2002,
        title="Other User Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Computing",
    )
    initial_count = PatentApplication.objects.count()
    principal = make_principal(
        user_id=1001,
        permissions=("pms.application.view_self", "pms.report.view_self"),
        modules=("pms",),
        kind="faculty",
        roles=("Applicant",),
        active_role="Applicant",
    )
    visible_ids = list(visible_applications(principal).values_list("id", flat=True))
    assert foreign_app.id not in visible_ids
    assert PatentApplication.objects.count() == initial_count


def test_br_tc_003_permitted_access_to_reports_within_authorized_pms_scope():
    """BR-TC-003 | BR-PMS-005: permitted access to reports and analytics within authorized PMS scope."""
    in_scope_app = submit_application(
        applicant_user_id=1001,
        title="AI In Scope",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    PmsRoleAssignment.objects.create(
        user_id=3001,
        role="Director",
        is_active=True,
        domain="AI",
    )
    director = make_principal(
        user_id=3001,
        permissions=("pms.application.review", "pms.report.view"),
        modules=("pms",),
        kind="faculty",
        roles=("Director",),
        active_role="Director",
    )
    visible_ids = list(visible_applications(director).values_list("id", flat=True))
    assert in_scope_app.id in visible_ids


def test_br_tc_004_prohibited_access_to_reports_outside_authorized_pms_scope():
    """BR-TC-004 | BR-PMS-005: prohibited access to reports and analytics outside authorized PMS scope."""
    out_of_scope_app = submit_application(
        applicant_user_id=1001,
        title="Biotech Out Of Scope",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Biotech",
    )
    initial_count = PatentApplication.objects.count()
    PmsRoleAssignment.objects.create(
        user_id=3001,
        role="Director",
        is_active=True,
        domain="AI",
    )
    director = make_principal(
        user_id=3001,
        permissions=("pms.application.review", "pms.report.view"),
        modules=("pms",),
        kind="faculty",
        roles=("Director",),
        active_role="Director",
    )
    visible_ids = list(visible_applications(director).values_list("id", flat=True))
    assert out_of_scope_app.id not in visible_ids
    assert PatentApplication.objects.count() == initial_count


def test_br_tc_005_permitted_workflow_oversight_within_director_domain():
    """BR-TC-005 | BR-PMS-006: permitted workflow oversight within Director's domain."""
    app = submit_application(
        applicant_user_id=1001,
        title="Domain App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    PmsRoleAssignment.objects.create(
        user_id=3001,
        role="Director",
        is_active=True,
        domain="AI",
    )
    require_director_scope(app, 3001)
    app.refresh_from_db()
    assert app.domain == "AI"


def test_br_tc_006_prohibited_workflow_oversight_outside_director_domain():
    """BR-TC-006 | BR-PMS-006: prohibited workflow oversight outside Director's domain."""
    app = submit_application(
        applicant_user_id=1001,
        title="Other Domain App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Energy",
    )
    PmsRoleAssignment.objects.create(
        user_id=3001,
        role="Director",
        is_active=True,
        domain="AI",
    )
    with pytest.raises(NotPermittedError):
        require_director_scope(app, 3001)
    app.refresh_from_db()
    assert app.domain == "Energy"


def test_br_tc_126_permitted_access_with_valid_pms_role_assignment():
    """BR-TC-126 | BR-PMS-126: permitted access with valid PMS role assignment."""
    app = submit_application(
        applicant_user_id=1001,
        title="Valid Role App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    principal = make_principal(
        user_id=1001,
        permissions=("pms.application.view_self",),
        modules=("pms",),
        kind="faculty",
        roles=("Applicant",),
        active_role="Applicant",
    )
    assert PatentApplication.objects.filter(pk=app.pk).exists()
    assert visible_applications(principal).filter(pk=app.pk).count() == 1


def test_br_tc_127_prohibited_access_without_valid_pms_role_assignment():
    """BR-TC-127 | BR-PMS-126: prohibited access without a valid PMS role assignment."""
    submit_application(
        applicant_user_id=1001,
        title="Restricted App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    initial_count = PatentApplication.objects.count()
    unassigned = make_principal(
        user_id=9999,
        permissions=(),
        modules=(),
        kind="student",
        roles=(),
        active_role="",
    )
    assert visible_applications(unassigned).count() == 0
    assert PatentApplication.objects.count() == initial_count


def test_br_tc_130_confidential_patent_information_protected_by_rbac():
    """BR-TC-130 | BR-PMS-130: confidential patent information protected by role-based access control."""
    app = submit_application(
        applicant_user_id=1001,
        title="Confidential Patent",
        abstract="Confidential Abstract",
        detailed_description="Confidential Description",
        claims="Confidential Claims",
        domain="Defense",
    )
    unauthorized = make_principal(
        user_id=4004,
        permissions=("pms.application.view_self",),
        modules=("pms",),
        kind="faculty",
        roles=("Applicant",),
        active_role="Applicant",
    )
    authorized_owner = make_principal(
        user_id=1001,
        permissions=("pms.application.view_self",),
        modules=("pms",),
        kind="faculty",
        roles=("Applicant",),
        active_role="Applicant",
    )
    assert visible_applications(unauthorized).filter(pk=app.pk).count() == 0
    assert visible_applications(authorized_owner).filter(pk=app.pk).count() == 1


def test_br_tc_131_pms_maintains_single_active_pcc_admin_oversight_role():
    """BR-TC-131 | BR-PMS-131: PMS maintains exactly one active PCC_ADMIN oversight role."""
    PmsRoleAssignment.objects.create(user_id=7001, role="PCC_ADMIN", is_active=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        PmsRoleAssignment.objects.create(user_id=7002, role="PCC_ADMIN", is_active=True)
    assert PmsRoleAssignment.objects.filter(role="PCC_ADMIN", is_active=True).count() == 1

    app = submit_application(
        applicant_user_id=1001,
        title="Conflict Check",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    with pytest.raises(ConflictOfInterestError):
        assign_director(
            application_id=app.id,
            director_user_id=1001,
            assigned_by_user_id=7001,
        )
    app.refresh_from_db()
    assert app.assigned_director_user_id is None
