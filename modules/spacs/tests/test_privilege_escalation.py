"""Privilege escalation tests for SPACS API endpoints."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session

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


def test_student_cannot_announce_cycle(stub_iam):
    """Students without spacs.cycle.create must be refused 403."""
    c = _client(stub_iam, user_id=101, role="student", permissions=("spacs.scheme.view",))
    res = c.post(
        "/api/v1/spacs/cycles",
        {
            "scheme_id": 1,
            "academic_year": "2026-2027",
            "application_start_date": "2026-08-01T00:00:00Z",
            "application_end_date": "2026-08-30T00:00:00Z",
        },
        format="json",
    )
    assert res.status_code == 403


def test_student_cannot_verify_applications(stub_iam):
    """Students cannot access verification queue."""
    c = _client(stub_iam, user_id=101, role="student", permissions=("spacs.scheme.view",))
    res = c.get("/api/v1/spacs/verifications")
    assert res.status_code == 403


def test_assistant_cannot_approve_decisions(stub_iam):
    """Assistants with spacs.application.review cannot make final sanction."""
    c = _client(
        stub_iam,
        user_id=201,
        role="spacs_assistant",
        permissions=("spacs.scheme.view", "spacs.application.review"),
    )
    res = c.post(
        "/api/v1/spacs/decisions/action",
        {
            "application_id": 1,
            "decision_stage": "final_sanction",
            "outcome": "approved",
        },
        format="json",
    )
    assert res.status_code == 403


def test_user_without_module_grant_is_refused(stub_iam):
    """User without spacs module grant gets 403."""
    c = _client(stub_iam, user_id=301, role="student", permissions=(), modules=())
    res = c.get("/api/v1/spacs/schemes")
    assert res.status_code == 403
