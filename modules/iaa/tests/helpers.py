"""Builders shared by the IAA tests: one actor per role, a published policy, ready records."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from fusion_auth.client import UserRef
from modules.iaa import registry
from modules.iaa.domain import roles
from modules.iaa.services import records

FACULTY = "faculty"
DOC = {"title": "Invoice", "link": "https://files.example/invoice.pdf"}

POLICY = {
    "approval_timeout_hours": 48,
    "ta_high_value_threshold": "25000",
    "budget_check_required": True,
    "request_types": ["voucher", "reimbursement"],
    "required_documents": {"expense": 1, "ta": 1},
    "routes": [
        {"kind": "expense", "min_amount": "0", "max_amount": "50000",
         "levels": [roles.HOD], "escalation_designation": roles.DEAN},
        {"kind": "expense", "min_amount": "50000",
         "levels": [roles.HOD, roles.DEAN], "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0",
         "levels": [roles.HOD], "escalation_designation": roles.DEAN},
    ],
    "anomaly_resolvers": {
        "budget": [roles.FINANCE, roles.DEAN],
        "policy": [roles.FINANCE, roles.DIRECTOR],
        "financial": [roles.AUDITOR, roles.DIRECTOR],
    },
}


def _user(uid: int, name: str, department: str = "CSE") -> UserRef:
    return UserRef(user_id=uid, username=f"u{uid}", display_name=name, kind="employee",
                   department=department)


USERS = {
    101: _user(101, "Creator"), 102: _user(102, "Other Faculty"),
    201: _user(201, "Finance"), 301: _user(301, "HoD CSE"),
    304: _user(304, "HoD ECE", "ECE"), 302: _user(302, "Dean"), 303: _user(303, "Director"),
    401: _user(401, "Auditor"), 501: _user(501, "Admin"),
}


def actor(user_id: int, role: str, *, permissions=None):
    """A principal acting in `role`, holding exactly what the registry grants that role."""
    grants = registry.ROLE_GRANTS[role] if permissions is None else permissions
    return make_principal(user_id=user_id, kind="employee", roles=(role,), active_role=role,
                          permissions=grants, modules=("iaa",))


def cast():
    return SimpleNamespace(
        creator=actor(101, FACULTY), other=actor(102, FACULTY),
        finance=actor(201, roles.FINANCE), hod=actor(301, roles.HOD),
        hod_ece=actor(304, roles.HOD), dean=actor(302, roles.DEAN),
        director=actor(303, roles.DIRECTOR), auditor=actor(401, roles.AUDITOR),
        admin=actor(501, roles.SYSTEM_ADMIN))


def api_client(stub_iam, user_id: int, role: str, *, permissions=None, modules=("iaa",)):
    """One client at a time: the stub IAM holds a single session."""
    grants = registry.ROLE_GRANTS[role] if permissions is None else permissions
    stub_iam(make_session(user_id=user_id, kind="employee", roles=(role,), active_role=role,
                          permissions=grants, modules=modules), users=USERS)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def new_expense(creator, *, amount="10000", department="CSE", request_type="voucher",
                docs: int = 1, submit: bool = True):
    record = records.create_expense(creator, department=department, request_type=request_type,
                                    title="Lab consumables", description="Soldering kits",
                                    amount=Decimal(amount))
    for _ in range(docs):
        records.add_document(creator, record.pk, **DOC)
    return records.submit(creator, record.pk) if submit else record


def new_ta(creator, *, amount="10000", department="CSE", docs: int = 1):
    today = timezone.localdate()
    return records.create_ta(
        creator, department=department, amount=Decimal(amount), purpose="Conference in Pune",
        trip_start=today - timedelta(days=5), trip_end=today - timedelta(days=3),
        documents=[DOC] * docs)
