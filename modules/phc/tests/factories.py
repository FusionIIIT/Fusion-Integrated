"""Principals per acting role, built from registry.ROLE_GRANTS so a test can never hold a typo."""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    InventoryItem,
    PatientVisit,
    Prescription,
    ReimbursementPolicy,
)
from modules.phc.registry import ROLE_GRANTS

STUDENT_ID = 1001
EMPLOYEE_ID = 2001
OTHER_EMPLOYEE_ID = 2002
PHC_STAFF_ID = 3001
OTHER_STAFF_ID = 3002
ACCOUNTS_ID = 4001
AUTHORITY_ID = 5001

KIND_OF = {"student": "student", "faculty": "faculty", "staff": "staff",
           "PHC Staff": "staff", "Accounts & Audit": "staff", "Approving Authority": "faculty"}


def session_for(role: str, user_id: int, *, modules=("phc",), extra=(), drop=()):
    perms = (set(ROLE_GRANTS[role]) | set(extra)) - set(drop)
    return make_session(user_id=user_id, permissions=perms, modules=modules,
                        kind=KIND_OF[role], roles=(role,), active_role=role)


def client_as(stub_iam, role: str, user_id: int, *, users=None, **kw) -> APIClient:
    stub_iam(session_for(role, user_id, **kw), users=users)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    return client


def visit_for(patient_id: int, *, recorded_by: int = PHC_STAFF_ID,
              on: date | None = None) -> PatientVisit:
    visit = PatientVisit.objects.create(patient_user_id=patient_id,
                                        visit_date=on or timezone.localdate(),
                                        complaint="Fever", diagnosis="Viral fever",
                                        recorded_by_user_id=recorded_by)
    Prescription.objects.create(visit=visit, medicine="Paracetamol 500mg", dosage="1-0-1",
                                duration_days=3)
    return visit


def policy(days: int = 30, includes_last_day: bool = True) -> ReimbursementPolicy:
    return ReimbursementPolicy.objects.create(
        effective_from=timezone.localdate() - timedelta(days=365), window_days=days,
        includes_last_day=includes_last_day)


def item(name: str = "Paracetamol 500mg", level: str = "100", threshold: str = "50"):
    return InventoryItem.objects.create(name=name, unit="strip", stock_level=level,
                                        reorder_threshold=threshold)
