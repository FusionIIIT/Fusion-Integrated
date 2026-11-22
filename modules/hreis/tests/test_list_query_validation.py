"""HTTP regression tests for the HR-EIS-only list query contract."""

from urllib.parse import urlsplit

import pytest
from rest_framework.test import APIClient

from modules.hreis.models import HRRequest
from modules.hreis.tests.actors import make_session

pytestmark = pytest.mark.django_db

LISTS = [
    ("service-records", "hradmin", ("hreis.service_record.view",)),
    ("requests", "staff", ("hreis.request.view",)),
    ("requests/approvals", "Registrar", ("hreis.approval.view", "hreis.request.view")),
    ("policies", "hradmin", ("hreis.policy.view",)),
    ("notifications", "staff", ("hreis.notification.view",)),
    ("audit", "hradmin", ("hreis.audit.view",)),
    ("compliance/requests", "hradmin", ("hreis.audit.view",)),
]


def client_for(stub_iam, role, permissions):
    stub_iam(
        make_session(
            user_id=10,
            kind="staff",
            roles=(role,),
            active_role=role,
            permissions=permissions,
            modules=("hreis",),
        )
    )
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return client


@pytest.mark.parametrize("path,role,permissions", LISTS)
@pytest.mark.parametrize(
    "query,code",
    [
        ("?family=ltc", "invalid_list_query"),
        ("?ordering=bad_field", "invalid_list_query"),
        ("?page_size=100", "invalid_list_query"),
        ("?user_id=99", "invalid_list_query"),
        ("?limit=0", "invalid_list_limit"),
        ("?limit=-1", "invalid_list_limit"),
        ("?limit=101", "invalid_list_limit"),
        ("?limit=" + "9" * 120, "invalid_list_limit"),
        ("?limit=1.5", "invalid_list_limit"),
        ("?limit=1&limit=2", "invalid_list_query"),
        ("?cursor=", "invalid_list_cursor"),
        ("?cursor=not-a-cursor", "invalid_list_cursor"),
        ("?cursor=" + "a" * 2049, "invalid_list_cursor"),
        ("?cursor=x&cursor=y", "invalid_list_query"),
    ],
)
def test_all_seven_list_endpoints_reject_hostile_inputs(stub_iam, path, role, permissions, query, code):
    client = client_for(stub_iam, role, permissions)
    response = client.get(f"/api/v1/hreis/{path}/{query}")
    assert response.status_code == 400, (path, query[:30], response.content)
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("path,role,permissions", LISTS)
def test_all_seven_list_endpoints_accept_bounded_limit(stub_iam, path, role, permissions):
    client = client_for(stub_iam, role, permissions)
    for limit in (1, 25, 100):
        response = client.get(f"/api/v1/hreis/{path}/?limit={limit}")
        assert response.status_code == 200, (path, response.content)
        assert isinstance(response.json()["results"], list)


def test_valid_cursor_navigation_is_unchanged(stub_iam):
    for _ in range(5):
        HRRequest.objects.create(user_id=10, family="leave", state="pending_authority")
    client = client_for(stub_iam, "staff", ("hreis.request.view",))
    first = client.get("/api/v1/hreis/requests/?limit=2")
    assert first.status_code == 200
    assert len(first.json()["results"]) == 2
    assert first.json()["next"]
    next_url = urlsplit(first.json()["next"])
    second = client.get(next_url.path + "?" + next_url.query)
    assert second.status_code == 200, second.content
    assert len(second.json()["results"]) == 2
    assert {row["id"] for row in first.json()["results"]}.isdisjoint(
        row["id"] for row in second.json()["results"]
    )


def test_missing_module_grant_still_precedes_query_validation(stub_iam):
    stub_iam(
        make_session(
            user_id=10,
            kind="staff",
            roles=("staff",),
            active_role="staff",
            permissions=("hreis.request.view",),
            modules=(),
        )
    )
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    response = client.get("/api/v1/hreis/requests/?bogus=123")
    assert response.status_code == 403
