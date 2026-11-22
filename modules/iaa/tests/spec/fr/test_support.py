"""HTTP helpers shared by the frozen FR specification tests."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import IamSession
from modules.iaa.domain import roles
from modules.iaa.services import decisions
from modules.iaa.tests.helpers import DOC, FACULTY, POLICY, USERS, api_client

BASE_URL = "/api/v1/iaa"
CREATOR = (101, FACULTY)
FINANCE = (201, roles.FINANCE)
HOD = (301, roles.HOD)
DEAN = (302, roles.DEAN)
DIRECTOR = (303, roles.DIRECTOR)
AUDITOR = (401, roles.AUDITOR)
ADMIN = (501, roles.SYSTEM_ADMIN)


class IaaHttp:
    """Perform real requests against the module API, changing IAM actor per request."""

    def __init__(self, stub_iam):
        self.stub_iam = stub_iam

    def request(self, who, method, path, body=None, expected_status=None):
        client = api_client(self.stub_iam, *who)
        url = f"{BASE_URL}{path}"
        if method == "get":
            response = client.get(url)
        elif method == "patch":
            response = client.patch(url, body or {}, format="json")
        elif method == "delete":
            response = client.delete(url)
        else:
            response = client.post(url, body or {}, format="json")
        if expected_status is not None:
            assert response.status_code == expected_status, response.content
        return response

    def get(self, who, path, expected_status=200):
        response = self.request(who, "get", path, expected_status=expected_status)
        return response if response.streaming else response.json()

    def post(self, who, path, body=None, expected_status=200):
        response = self.request(who, "post", path, body, expected_status)
        return response if response.streaming else response.json()

    def patch(self, who, path, body=None, expected_status=200):
        response = self.request(who, "patch", path, body, expected_status)
        return response if response.streaming else response.json()

    def expense_draft(self, *, user=CREATOR, department="CSE", request_type="voucher",
                      amount="10000", title="Lab kits", description="Soldering kits"):
        return self.post(user, "/records", {
            "kind": "expense", "department": department, "request_type": request_type,
            "title": title, "description": description, "amount": amount,
        }, expected_status=201)

    def submitted_expense(self, *, user=CREATOR, department="CSE", request_type="voucher",
                          amount="10000", title="Lab kits", description="Soldering kits"):
        draft = self.expense_draft(user=user, department=department, request_type=request_type,
                                   amount=amount, title=title, description=description)
        self.post(user, f"/records/{draft['id']}/documents", DOC, expected_status=201)
        return self.post(user, f"/records/{draft['id']}/submit")

    def submitted_ta(self, *, user=CREATOR, department="CSE", amount="10000", purpose="Conference",
                     documents=None):
        today = timezone.localdate()
        return self.post(user, "/records", {
            "kind": "ta", "department": department, "amount": amount, "purpose": purpose,
            "trip_start": str(today - timedelta(days=5)),
            "trip_end": str(today - timedelta(days=3)),
            "documents": [DOC] if documents is None else documents,
        }, expected_status=201)

    def validated(self, record_id, who=FINANCE, *, decision="verify", remarks=""):
        return self.post(who, f"/records/{record_id}/validate",
                         {"decision": decision, "remarks": remarks})

    def decide(self, record_id, who=HOD, *, decision="approve", remarks="Reviewed",
               expected_status=200):
        return self.post(who, f"/records/{record_id}/decision",
                         {"decision": decision, "remarks": remarks}, expected_status)

    def status(self, record_id, who=CREATOR):
        return self.get(who, f"/records/{record_id}")["status"]

    def history(self, record_id, who=CREATOR):
        return self.get(who, f"/records/{record_id}/history")

    def overdue(self):
        return decisions.escalate_overdue(at=timezone.now() + timedelta(hours=49))


def client_for_session(stub_iam, *, user_id, active_role, actor_roles, permissions):
    """Install a multi-role IAM session for role-context checks."""
    session: IamSession = make_session(
        user_id=user_id, kind="employee", roles=actor_roles, active_role=active_role,
        permissions=permissions, modules=("iaa",),
    )
    stub_iam(session=session, users=USERS)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def published_policy(run, *, routes=None, timeout=48, threshold="25000"):
    return run.post(ADMIN, "/config/policies", {
        **POLICY,
        "approval_timeout_hours": timeout,
        "ta_high_value_threshold": threshold,
        "routes": POLICY["routes"] if routes is None else routes,
    }, expected_status=201)
