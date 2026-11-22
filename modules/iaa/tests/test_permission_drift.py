"""Permission strings are free text in a test and in a view: a typo is granted by the fake and
refused in production. These tests fail when the codes in use and the codes declared drift apart.

Also the two gates apart, the plain user, and the role switch (IAA-BR-003, IAA-BR-501).
"""
import re
from pathlib import Path

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.iaa import registry
from modules.iaa.domain import roles
from modules.iaa.tests.helpers import FACULTY, USERS, api_client, new_expense

pytestmark = pytest.mark.django_db

MODULE_DIR = Path(__file__).resolve().parents[1]
DECLARED = {code for code, _ in registry.PERMISSIONS}
CODE = re.compile(r"""["'](iaa\.[a-z_]+\.[a-z_]+)["']""")
B = "/api/v1/iaa"


def _codes_in(folder: Path, *, skip_tests: bool) -> set[str]:
    found = set()
    for path in folder.rglob("*.py"):
        if path.name == "registry.py" or "migrations" in path.parts:
            continue
        if skip_tests and "tests" in path.parts:
            continue
        found |= set(CODE.findall(path.read_text()))
    return found


def test_every_code_the_server_checks_is_declared():
    used = _codes_in(MODULE_DIR, skip_tests=True)
    assert used and used <= DECLARED, used - DECLARED


def test_every_code_a_test_uses_is_declared():
    used = _codes_in(MODULE_DIR / "tests", skip_tests=False)
    assert used <= DECLARED, used - DECLARED


def test_every_grant_is_a_declared_code_and_every_code_is_granted_to_someone():
    granted = set().union(*registry.ROLE_GRANTS.values())
    assert granted <= DECLARED
    assert DECLARED - granted <= set(registry.SYSTEM_PERMISSIONS)


def test_the_system_permission_is_held_by_no_human_role():
    for role, grants in registry.ROLE_GRANTS.items():
        assert not set(registry.SYSTEM_PERMISSIONS) & set(grants), role


def test_every_nav_item_requires_a_declared_code():
    assert {i["required_permission"] for i in registry.NAV_ITEMS} <= DECLARED


# ── the two gates are different refusals ────────────────────────────────────────────────

def _client(stub_iam, *, permissions, modules):
    stub_iam(make_session(user_id=201, kind="employee", roles=(roles.FINANCE,),
                          active_role=roles.FINANCE, permissions=permissions,
                          modules=modules), users=USERS)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_the_permission_without_the_module_grant_is_refused(stub_iam):
    finance = registry.ROLE_GRANTS[roles.FINANCE]
    assert _client(stub_iam, permissions=finance, modules=()).get(
        f"{B}/records").status_code == 403


def test_the_module_grant_without_the_permission_is_refused(stub_iam):
    assert _client(stub_iam, permissions=(), modules=("iaa",)).get(
        f"{B}/records").status_code == 403


def test_both_together_are_let_in(stub_iam, people, configured):
    new_expense(people.creator)
    finance = registry.ROLE_GRANTS[roles.FINANCE]
    assert _client(stub_iam, permissions=finance, modules=("iaa",)).get(
        f"{B}/records").status_code == 200


# ── the plain user (IAA-BR-501) ─────────────────────────────────────────────────────────

def test_the_plain_faculty_user_can_do_their_own_work_and_nothing_else(
        stub_iam, people, configured):
    client = api_client(stub_iam, 101, FACULTY)
    made = client.post(f"{B}/records", {"kind": "expense"}, format="json")
    assert made.status_code == 201
    assert client.get(f"{B}/records").status_code == 200
    assert client.get(f"{B}/notifications").status_code == 200
    observed = client.get(f"{B}/observations")                  # their own, as respondent
    assert observed.status_code == 200 and observed.json()["results"] == []
    for url in ("/anomalies", "/reports/summary", "/config/policies"):
        assert client.get(f"{B}{url}").status_code == 403, url
    pk = made.json()["id"]
    for url in (f"/records/{pk}/validate", f"/records/{pk}/decision",
                f"/records/{pk}/processing"):
        assert client.post(f"{B}{url}", {}, format="json").status_code == 403, url


# ── the role switch: one person, two designations ───────────────────────────────────────

def test_a_person_holding_two_roles_gets_only_the_acting_roles_view(
        stub_iam, people, configured):
    pk = new_expense(people.creator).pk
    both = registry.ROLE_GRANTS[roles.FINANCE]
    stub_iam(make_session(user_id=201, kind="employee", roles=(roles.FINANCE, FACULTY),
                          active_role=FACULTY, permissions=registry.ROLE_GRANTS[FACULTY],
                          modules=("iaa",)), users=USERS)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    assert client.get(f"{B}/records").json()["results"] == []          # acting as faculty
    assert client.post(f"{B}/records/{pk}/validate", {}, format="json").status_code == 403

    stub_iam(make_session(user_id=201, kind="employee", roles=(roles.FINANCE, FACULTY),
                          active_role=roles.FINANCE, permissions=both, modules=("iaa",)),
             users=USERS)
    assert [r["id"] for r in client.get(f"{B}/records").json()["results"]] == [pk]
    assert client.post(f"{B}/records/{pk}/validate", {}, format="json").status_code == 200
