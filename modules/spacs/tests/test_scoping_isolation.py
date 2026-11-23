"""Scoping isolation tests: Person A cannot see or mutate Person B's records."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import SpacsApplication, SpacsCatalogueEntry

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id=101):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="student",
            roles=("student",),
            active_role="student",
            permissions=("spacs.scheme.view", "spacs.application.view", "spacs.application.update"),
            modules=("spacs",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


@pytest.fixture
def sample_world():
    scheme = SpacsCatalogueEntry.objects.create(
        scheme_code="SCH-MCM-2026",
        name="MCM Scheme",
        scheme_type="scholarship",
        status="published",
    )
    app1 = SpacsApplication.objects.create(
        application_id="SPACS-APP-001",
        catalogue_entry=scheme,
        applicant_user_id=101,
        academic_cycle="2026-27",
        state="submitted",
        cpi=8.5,
        family_income=200000,
    )
    app2 = SpacsApplication.objects.create(
        application_id="SPACS-APP-002",
        catalogue_entry=scheme,
        applicant_user_id=102,
        academic_cycle="2026-27",
        state="submitted",
        cpi=9.0,
        family_income=150000,
    )
    return app1, app2


def test_student_cannot_view_other_student_application(stub_iam, sample_world):
    """Student 101 attempting to fetch Student 102's application gets 404."""
    _app1, app2 = sample_world
    c = _client(stub_iam, user_id=101)
    res = c.get(f"/api/v1/spacs/applications/{app2.id}")
    assert res.status_code == 404


def test_student_cannot_withdraw_other_student_application(stub_iam, sample_world):
    """Student 101 attempting to withdraw Student 102's application gets 404."""
    _app1, app2 = sample_world
    c = _client(stub_iam, user_id=101)
    res = c.post(
        f"/api/v1/spacs/applications/{app2.id}/withdraw", {"reason": "Malicious"}, format="json"
    )
    assert res.status_code == 404
