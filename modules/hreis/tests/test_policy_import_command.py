"""Policy file import requires verified IAM HR authority and explicit source data."""

import json
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from fusion_auth.client import IamSession
from modules.hreis.management.commands import hreis_import_policies
from modules.hreis.models import AuditEvent, HRPolicyVersion

pytestmark = pytest.mark.django_db


def _file(tmp_path):
    now = timezone.now()
    path = tmp_path / "institute-rules.json"
    payload = {
        "policies": [
            {
                "family": "leave",
                "version": 7,
                "effective_from": (now - timedelta(days=1)).isoformat(),
                "effective_until": (now + timedelta(days=2)).isoformat(),
                "parameters": {
                    "eligibility": {"staff": {"Casual": True}},
                    "routes": [
                        {
                            "employee_kind": "staff",
                            "department": "CSE",
                            "authorities": ["Registrar"],
                        }
                    ],
                },
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def _iam(monkeypatch, *, role="hradmin", permissions=("hreis.policy.manage",)):
    session = IamSession(
        user_id=99,
        username="authorized-test-hr",
        display_name="Test HR operator",
        kind="staff",
        active_role=role,
        roles=(role,),
        permissions=frozenset(permissions),
        modules=("hreis",),
    )
    monkeypatch.setattr(
        hreis_import_policies,
        "get_client",
        lambda: SimpleNamespace(resolve_session=lambda *, auth_token: session),
    )
    monkeypatch.setenv("HREIS_OPERATOR_IAM_TOKEN", "synthetic-iam-session-only")


def test_explicit_iam_authenticated_policy_import_is_atomic_idempotent(tmp_path, monkeypatch):
    # HR-UC-017, HR-CFR-004, BR-HR-025/029: operator provides ALL institute
    # values; command never generates quota or approval routes.
    file, _payload = _file(tmp_path)
    _iam(monkeypatch)
    result = StringIO()
    call_command("hreis_import_policies", policy_file=str(file), stdout=result)
    assert "1 approved version(s) imported" in result.getvalue()
    saved = HRPolicyVersion.objects.get(family="leave", version=7)
    assert saved.approved_by_user_id == 99
    assert saved.parameters["routes"][0]["authorities"] == ["Registrar"]
    assert AuditEvent.objects.get(event_key="policy:trusted-policy-import-leave-7")
    result = StringIO()
    call_command("hreis_import_policies", policy_file=str(file), stdout=result)
    assert "1 identical version(s) already existed" in result.getvalue()
    assert HRPolicyVersion.objects.count() == 1
    assert AuditEvent.objects.count() == 1


def test_import_fails_without_authorized_iam_or_when_file_changes(tmp_path, monkeypatch):
    file, payload = _file(tmp_path)
    monkeypatch.delenv("HREIS_OPERATOR_IAM_TOKEN", raising=False)
    with pytest.raises(CommandError, match="Set HREIS_OPERATOR_IAM_TOKEN"):
        call_command("hreis_import_policies", policy_file=str(file))
    assert not HRPolicyVersion.objects.exists()
    _iam(monkeypatch, role="faculty")
    with pytest.raises(CommandError, match="HR Administrator"):
        call_command("hreis_import_policies", policy_file=str(file))
    assert not HRPolicyVersion.objects.exists()
    _iam(monkeypatch)
    call_command("hreis_import_policies", policy_file=str(file), stdout=StringIO())
    payload["policies"][0]["parameters"]["eligibility"]["staff"]["Casual"] = False
    file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CommandError, match="different immutable fields"):
        call_command("hreis_import_policies", policy_file=str(file))
    assert (
        HRPolicyVersion.objects.get(family="leave").parameters["eligibility"]["staff"]["Casual"]
        is True
    )
