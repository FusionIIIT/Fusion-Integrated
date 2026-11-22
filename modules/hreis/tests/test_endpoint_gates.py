"""Every HR-EIS operation independently requires both the module and permission gates."""

import pytest
from rest_framework.test import APIClient

from modules.hreis.registry import PERMISSIONS
from modules.hreis.tests.actors import make_session

pytestmark = pytest.mark.django_db
OPERATIONS = [
    ("get", "service-records/me/"),
    ("get", "service-records/"),
    ("post", "service-records/"),
    ("get", "service-records/99999/"),
    ("patch", "service-records/99999/"),
    ("get", "requests/"),
    ("get", "requests/approvals/"),
    ("get", "requests/99999/"),
    ("get", "leave/balances/"),
    ("post", "leave-balances/credits/"),
    ("post", "requests/leave/"),
    ("post", "requests/claims/"),
    ("post", "requests/appraisals/"),
    ("post", "requests/99999/assign-reviewers/"),
    ("post", "requests/99999/appraisal-decision/"),
    ("post", "requests/99999/verify-claim/"),
    ("post", "requests/99999/financial-review/"),
    ("post", "requests/99999/financial-processing/"),
    ("post", "requests/99999/decision/"),
    ("get", "policies/"),
    ("post", "policies/"),
    ("get", "notifications/"),
    ("post", "notifications/99999/read/"),
    ("get", "audit/"),
    ("get", "compliance/requests/"),
    ("get", "compliance/requests/99999/"),
]


@pytest.mark.parametrize("method,path", OPERATIONS)
@pytest.mark.parametrize("missing", ["module", "permission"])
def test_every_operation_refuses_each_missing_gate(stub_iam, method, path, missing):
    stub_iam(
        make_session(
            user_id=99,
            kind="staff",
            active_role="hradmin",
            roles=("hradmin",),
            modules=() if missing == "module" else ("hreis",),
            permissions=tuple(code for code, _ in PERMISSIONS) if missing == "module" else (),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    response = getattr(client, method)("/api/v1/hreis/" + path, {}, format="json")
    assert response.status_code == 403, (method, path, missing, response.content)
