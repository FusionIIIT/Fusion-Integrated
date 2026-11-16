"""End-to-end user journeys through HTTP layer."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import SpacsCatalogueEntry

pytestmark = pytest.mark.django_db


def _client_for(stub_iam, user_id, role, permissions):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="student" if role == "student" else "staff",
            roles=(role,),
            active_role=role,
            permissions=permissions,
            modules=("spacs",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_full_scholarship_journey(stub_iam):
    """Journey: publish scheme -> student apply -> assistant verify -> convener approve."""
    now = timezone.now()
    scheme = SpacsCatalogueEntry.objects.create(
        scheme_code="JOURNEY-SCH-01",
        name="Institute Silver Scholarship",
        scheme_type="scholarship",
        status="published",
        min_cpi=7.0,
        max_family_income=250000,
        application_window_start=now - timedelta(days=2),
        application_window_end=now + timedelta(days=15),
        academic_cycle="2026-27",
    )

    # 1. Student applies
    client_student = _client_for(
        stub_iam,
        user_id=701,
        role="student",
        permissions=("spacs.scheme.view", "spacs.application.create", "spacs.application.view"),
    )
    apply_res = client_student.post(
        "/api/v1/spacs/applications",
        {
            "scheme_code": scheme.scheme_code,
            "academic_cycle": "2026-27",
            "cpi": 8.0,
            "family_income": 180000,
        },
        format="json",
    )
    assert apply_res.status_code == 201
    app_id = apply_res.data["id"]
    app_code = apply_res.data["application_id"]

    # 2. Assistant checks verification queue and verifies
    client_asst = _client_for(
        stub_iam,
        user_id=801,
        role="spacs_assistant",
        permissions=("spacs.scheme.view", "spacs.application.review"),
    )
    queue_res = client_asst.get("/api/v1/spacs/verifications")
    assert queue_res.status_code == 200
    assert len(queue_res.data) >= 1

    verify_res = client_asst.post(
        f"/api/v1/spacs/verifications/{app_id}/action",
        {
            "action": "verify",
            "notes": "All documents verified in order.",
        },
        format="json",
    )
    assert verify_res.status_code == 200

    # 3. Convener approves
    client_convener = _client_for(
        stub_iam,
        user_id=901,
        role="spacs_convener",
        permissions=("spacs.scheme.view", "spacs.application.approve"),
    )
    approve_res = client_convener.post(
        "/api/v1/spacs/decisions/action",
        {
            "application_id": app_code,
            "outcome": "approved",
            "reason": "Approved by Convener",
        },
        format="json",
    )
    assert approve_res.status_code == 200
