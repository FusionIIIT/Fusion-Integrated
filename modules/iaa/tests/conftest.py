from datetime import date

import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.iaa.domain.rules import Role
from modules.iaa.models import (
    ApprovalRoute,
    Budget,
    Department,
    FinancialYear,
    Policy,
    RoleAssignment,
)

BASIC, FINANCE, HOD, DEAN, DIRECTOR, AUDITOR, ADMIN, OTHER = range(101, 109)
PEOPLE = {
    uid: UserRef(
        user_id=uid,
        username=f"iaa{uid}",
        display_name=f"Synthetic {uid}",
        kind="staff",
        department="CSE",
    )
    for uid in range(101, 111)
}
GRANTS = {
    BASIC: Role.BASIC,
    FINANCE: Role.FINANCE,
    HOD: Role.HOD,
    DEAN: Role.DEAN,
    DIRECTOR: Role.DIRECTOR,
    AUDITOR: Role.AUDITOR,
    ADMIN: Role.ADMIN,
    OTHER: Role.BASIC,
}


@pytest.fixture
def world(db, stub_iam):
    with freeze_time("2027-03-01 09:00:00"):
        stub_iam(users=PEOPLE)
        for uid, role in GRANTS.items():
            RoleAssignment.objects.create(
                user_id=uid, role=role, department="" if role == Role.ADMIN else "CSE"
            )
        year = FinancialYear.objects.create(
            name="2026-27", starts_on=date(2026, 4, 1), ends_on=date(2027, 3, 31)
        )
        Department.objects.create(code="CSE", finance_user_id=FINANCE)
        Policy.objects.create(
            name="Institute",
            ta_approval_threshold=500,
            ta_max_daily_amount=1000,
            anomaly_resolver_id=FINANCE,
            anomaly_resolver_role=Role.FINANCE,
            anomaly_escalation_id=AUDITOR,
            anomaly_escalation_role=Role.AUDITOR,
        )
        Budget.objects.create(department="CSE", year=year, allocated=10000)
        for kind in ("expense", "ta"):
            ApprovalRoute.objects.create(
                name=kind,
                kind=kind,
                department="CSE",
                steps=[
                    {"user_id": HOD, "role": Role.HOD, "timeout_hours": 24},
                    {"user_id": DEAN, "role": Role.DEAN, "timeout_hours": 48},
                    {"user_id": DIRECTOR, "role": Role.DIRECTOR, "timeout_hours": 72},
                ],
            )
        yield


@pytest.fixture
def client_as(stub_iam):
    def create(
        uid,
        role=None,
        *,
        permissions=("institute_accounts_audits.workspace.access",),
        modules=("institute_accounts_audits",),
    ):
        active = role or GRANTS.get(uid, Role.BASIC)
        stub_iam(
            make_session(
                user_id=uid,
                kind="staff",
                roles=(active,),
                active_role=active,
                permissions=permissions,
                modules=modules,
            ),
            users=PEOPLE,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-iaa", HTTP_X_IAA_ROLE=str(active))
        return client

    return create


def draft(client, **overrides):
    body = {
        "kind": "expense",
        "request_type": "voucher",
        "department": "CSE",
        "amount": "100.00",
        "description": "Synthetic conference supplies",
        "documents": ["https://example.org/evidence.pdf"],
        **overrides,
    }
    return client.post("/api/v1/iaa/requests", body, format="json")


def action(client, pk, name, **data):
    return client.post(f"/api/v1/iaa/requests/{pk}/{name}", data, format="json")


def submitted(client_as, **overrides):
    c = client_as(BASIC)
    response = draft(c, **overrides)
    assert response.status_code == 201, response.json()
    pk = response.json()["id"]
    if overrides.get("kind") != "ta":
        response = action(c, pk, "submit")
        assert response.status_code == 200, response.json()
    return pk


def validated(client_as, **overrides):
    pk = submitted(client_as, **overrides)
    response = action(client_as(FINANCE), pk, "validate", remarks="Documents and policy checked")
    assert response.status_code == 200, response.json()
    return pk
