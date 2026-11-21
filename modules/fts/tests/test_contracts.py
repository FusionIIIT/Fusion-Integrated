"""Tests for FTS contracts and integration endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from modules.fts.contracts import (
    create_module_tracked_file,
    get_file_statuses,
    get_files_for_users,
)
from modules.fts.services.files import create_file
from modules.fts.tests.conftest import make_fts_session as make_session

pytestmark = pytest.mark.django_db


def test_contracts_public_api():
    # Empty inputs return empty dicts without queries
    assert get_file_statuses([]) == {}
    assert get_files_for_users([]) == {}

    f = create_file(
        subject="Contracts Test File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )

    statuses = get_file_statuses([f.id])
    assert f.id in statuses
    assert statuses[f.id].status == "CIRCULATED"
    assert statuses[f.id].current_holder_user_id == 202

    user_files = get_files_for_users([202])
    assert 202 in user_files
    assert len(user_files[202]) == 1
    assert user_files[202][0].file_id == f.id

    # Create tracked file from another module
    created_dto = create_module_tracked_file(
        subject="Module Tracked File",
        comment_text="Tracked from Leave module.",
        creator_user_id=101,
        creator_username="fac_101",
        creator_role="Assistant Professor",
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    assert created_dto.status == "CIRCULATED"
    assert created_dto.current_holder_user_id == 202


def test_integration_endpoint_requires_grant(stub_iam):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token service-token")

    # Without permission -> 403
    stub_iam(make_session(user_id=888, permissions=()))
    res_deny = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Integration File",
            "comment": "Initial comment.",
            "recipient_user_id": 202,
        },
        format="json",
    )
    assert res_deny.status_code == status.HTTP_403_FORBIDDEN

    # With permission -> 201
    stub_iam(make_session(user_id=888, permissions=("fts.integration.access",)))
    res_ok = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Integration File",
            "comment": "Initial comment.",
            "recipient_user_id": 202,
            "recipient_username": "staff_202",
            "recipient_role": "Junior Superintendent",
        },
        format="json",
    )
    assert res_ok.status_code == status.HTTP_201_CREATED
