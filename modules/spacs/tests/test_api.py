"""API tests for the SPACS module."""
from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import (
    AwardCycle,
    ScholarshipApplication,
    SchemeCatalogue,
    SchemePolicyVersion,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def scheme():
    now = timezone.now()
    s = SchemeCatalogue.objects.create(
        code="mcm",
        name="Merit-cum-Means",
        scheme_type="scholarship",
        status="published",
    )
    SchemePolicyVersion.objects.create(
        scheme=s,
        version_number=1,
        title="MCM 2026",
        eligibility_criteria={"min_cpi": 6.5},
        status="published",
        effective_from=now.date() - timedelta(days=10),
        effective_to=now.date() + timedelta(days=100),
        policy_approval_reference="Senate 12",
    )
    return s


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("spacs",))
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def test_unauthenticated_request_is_401():
    c = APIClient()
    resp = c.get("/api/v1/spacs/catalogue/")
    assert resp.status_code == 401


def test_missing_module_grant_is_403(stub_iam):
    c = _client(stub_iam, user_id=1001, modules=("placement_cell",))
    resp = c.get("/api/v1/spacs/catalogue/")
    assert resp.status_code == 403


def test_catalogue_list(stub_iam, scheme):
    c = _client(stub_iam, user_id=1001, permissions=("spacs.catalogue.view",))
    resp = c.get("/api/v1/spacs/catalogue/")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["code"] == "mcm"


def test_student_sees_only_own_applications(stub_iam, scheme):
    ver = scheme.versions.first()
    ScholarshipApplication.objects.create(
        application_number="SPACS-1001",
        student_user_id=1001,
        scheme=scheme,
        policy_version=ver,
        academic_cycle="2026-27",
        status="submitted",
    )
    ScholarshipApplication.objects.create(
        application_number="SPACS-2002",
        student_user_id=2002,
        scheme=scheme,
        policy_version=ver,
        academic_cycle="2026-27",
        status="submitted",
    )

    c = _client(stub_iam, user_id=1001, permissions=("spacs.application.view_self",))
    resp = c.get("/api/v1/spacs/applications/")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["student_user_id"] == 1001


def test_foreign_application_is_404_not_403(stub_iam, scheme):
    """Architecture requirement: ownership scoping in selector yields 404, not 403."""
    ver = scheme.versions.first()
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-2002",
        student_user_id=2002,
        scheme=scheme,
        policy_version=ver,
        academic_cycle="2026-27",
        status="submitted",
    )

    c = _client(stub_iam, user_id=1001, permissions=("spacs.application.view_self",))
    resp = c.get(f"/api/v1/spacs/applications/{app.id}/")
    assert resp.status_code == 404


def test_convener_sees_all_applications(stub_iam, scheme):
    ver = scheme.versions.first()
    ScholarshipApplication.objects.create(
        application_number="SPACS-1001",
        student_user_id=1001,
        scheme=scheme,
        policy_version=ver,
        academic_cycle="2026-27",
        status="verified",
    )
    ScholarshipApplication.objects.create(
        application_number="SPACS-2002",
        student_user_id=2002,
        scheme=scheme,
        policy_version=ver,
        academic_cycle="2026-27",
        status="verified",
    )

    c = _client(stub_iam, user_id=3001, permissions=("spacs.application.approve",))
    resp = c.get("/api/v1/spacs/applications/")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 2
