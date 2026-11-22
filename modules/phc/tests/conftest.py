"""Shared PHC API test helpers."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session


@pytest.fixture
def phc_client(stub_iam):
    def make(*, uid=1001, kind="student", permissions=(), modules=("phc",)):
        stub_iam(make_session(user_id=uid, kind=kind, modules=modules, permissions=permissions))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-token")
        return client

    return make


@pytest.fixture
def visit(db):
    from modules.phc.models import PatientVisit

    return PatientVisit.objects.create(
        user_id=1001,
        visit_date="2026-10-01",
        chief_complaint="Fever",
        diagnosis="Viral fever",
        recorded_by_user_id=900,
    )


@pytest.fixture
def prescription(visit):
    from modules.phc.models import Prescription

    return Prescription.objects.create(
        user_id=visit.user_id,
        visit=visit,
        medicine_name="Paracetamol",
        dosage="500 mg",
        duration_days=3,
        prescribed_by_user_id=900,
        expense_date="2026-10-01",
    )
