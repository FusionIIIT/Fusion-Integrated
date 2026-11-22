"""The role model, checked against the spec and against the code that relies on it.

`registry/permissions.json` is what production grants. These tests pin it to the business
rules, and pin the code's permission strings to the registry, so neither can drift alone."""
import json
import re
from pathlib import Path

import pytest

from modules.mms import registry as mms_registry
from modules.mms.tests.helpers import ADMIN, CARETAKER, MMS_REGISTRY, ROLES, STUDENT, WARDEN, grants

MMS_DIR = Path(__file__).resolve().parents[1]
DECLARED = {p["code"] for p in MMS_REGISTRY["permissions"]}

# permission -> the ONLY roles the spec lets hold it.
OWNERS = {
    "mms.role.manage":                 {ADMIN},                        # BR-002..006
    "mms.window.manage":               {CARETAKER},                    # BR-008
    "mms.registration.self":           {STUDENT},                      # BR-009
    "mms.registration.review":         {CARETAKER},                    # BR-010
    "mms.deregistration.self":         {STUDENT},                      # BR-012
    "mms.deregistration.review":       {CARETAKER},                    # BR-010
    "mms.registration.view_oversight": {WARDEN},                       # BR-011
    "mms.menu.manage":                 {CARETAKER},                    # BR-039
    "mms.bill.manage":                 {CARETAKER},                    # BR-018
    "mms.bill.view_self":              {STUDENT},                      # BR-040
    "mms.feedback.submit":             {STUDENT},                      # BR-020
    "mms.feedback.view":               {CARETAKER, WARDEN},            # BR-020
    "mms.rebate.self":                 {STUDENT},                      # BR-021..024
    "mms.rebate.review":               {CARETAKER},                    # BR-025
    "mms.vacation.manage":             {CARETAKER},                    # BR-026
    "mms.vacation.respond":            {STUDENT},                      # BR-041
    "mms.special_food.self":           {STUDENT},                      # BR-028
    "mms.special_food.review":         {CARETAKER},                    # BR-029
    "mms.special_food.fulfill":        {CARETAKER},                    # BR-031, ISS-014
    "mms.announcement.publish":        {CARETAKER, WARDEN},            # BR-032
    "mms.report.operational":          {CARETAKER},                    # BR-034
    "mms.report.supervisory":          {WARDEN},                       # BR-034
}


@pytest.mark.parametrize(("perm", "owners"), OWNERS.items(), ids=OWNERS.keys())
def test_each_permission_is_held_by_exactly_the_roles_the_spec_names(perm, owners):
    held_by = {r for r in ROLES if perm in grants(r)}
    assert held_by == owners


def test_br005_the_mess_admin_holds_nothing_operational():
    """Only role assignment, plus the read-only menu/announcement views (menu access for
    the admin is an open question, ISS-MMS-012 — widen deliberately, not by accident)."""
    assert grants(ADMIN) == {"mms.role.manage", "mms.menu.view", "mms.announcement.view"}


def test_br011_the_warden_holds_no_decision_or_management_permission():
    decide = {p for p in grants(WARDEN)
              if p.endswith((".review", ".manage", ".fulfill", ".self", ".respond", ".submit"))}
    assert decide == set()


def test_students_hold_no_staff_permission():
    assert not {p for p in grants(STUDENT) if p.endswith((".review", ".manage", ".fulfill",
                                                          ".publish", ".view_oversight"))}


def test_nobody_but_students_can_act_on_their_own_behalf():
    for perm in (p for p in DECLARED if p.endswith((".self", ".submit", ".respond"))):
        assert {r for r in ROLES if perm in grants(r)} == {STUDENT}


def test_every_declared_permission_is_covered_by_this_matrix():
    """Add a permission and this fails until the spec owner for it is written down."""
    assert set(OWNERS) | {"mms.menu.view", "mms.announcement.view"} == DECLARED


def test_every_permission_string_the_code_checks_is_declared_in_the_registry():
    """A typo'd permission string is a check that nobody can ever pass (or everybody can)."""
    used = set()
    for path in MMS_DIR.glob("**/*.py"):
        if "tests" in path.parts or "migrations" in path.parts:
            continue
        used |= set(re.findall(r"has_permission\(\s*\"(mms\.[a-z_.]+)\"", path.read_text()))
    assert used, "found no permission checks — the regex is stale"
    assert used - DECLARED == set()


def test_every_declared_permission_is_actually_checked_somewhere():
    """A permission nothing checks grants nothing; it is dead weight in the role model."""
    source = "".join(p.read_text() for p in MMS_DIR.glob("**/*.py")
                     if "tests" not in p.parts and "migrations" not in p.parts)
    unused = {p for p in DECLARED if f'"{p}"' not in source}
    assert unused == set()


def test_navigation_only_points_at_permissions_the_role_model_declares():
    for item in mms_registry.NAV_ITEMS:
        assert item["required_permission"] in DECLARED, item["code"]


def test_every_nav_item_is_reachable_by_at_least_one_role():
    held = set().union(*(grants(r) for r in ROLES))
    for item in mms_registry.NAV_ITEMS:
        assert item["required_permission"] in held, item["code"]


def test_the_registry_json_matches_the_python_registry():
    """The two descriptions of the MMS nav must agree on the set of destinations."""
    json_items = {i["code"] for i in MMS_REGISTRY["nav"]["items"]}
    py_items = {i["code"] for i in mms_registry.NAV_ITEMS}
    assert json_items == py_items


def test_registry_file_is_valid_json_with_the_four_mms_roles():
    data = json.loads((MMS_DIR.parents[1] / "registry" / "permissions.json").read_text())
    assert set(data["modules"]["mms"]["grants"]) == set(ROLES)
