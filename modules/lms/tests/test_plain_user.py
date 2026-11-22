"""Tests ensuring plain users without LMS module grant are strictly refused (R1-02, R1-23)."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db


def test_plain_user_without_lms_grant_is_refused(stub_iam):
    # Principal has general session but NO "lms" module grant
    stub_iam(
        make_session(
            user_id=7777,
            kind="student",
            permissions=("lms.workspace.view",),  # Even if permission string exists, module grant is missing
            modules=("placement_cell",),  # Not 'lms'
        )
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    res = client.get("/api/v1/lms/courses/")
    assert res.status_code == 403
    assert "error" in res.data


def test_unauthenticated_request_is_refused():
    client = APIClient()
    res = client.get("/api/v1/lms/courses/")
    assert res.status_code == 401
