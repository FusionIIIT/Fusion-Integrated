"""Pure rules and state tables, no database (Steps 5.3 and 5.4)."""

from datetime import UTC, datetime, time, timedelta
from itertools import pairwise, product

import pytest

from modules.department.domain import roles
from modules.department.domain import rules as r
from modules.department.domain import state_machine as sm
from modules.department.domain.errors import ActorNotAllowed, InvalidTransition, RuleViolation
from modules.department.domain.roles import ActorContext

ALL_ACTORS = (
    roles.STUDENT,
    roles.FACULTY,
    roles.HOD,
    roles.DEPT_ADMIN,
    roles.CENTRAL,
    None,
)


# -- roles -------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("active", "kind", "role", "dept"),
    [
        ("ug_student", "student", roles.STUDENT, None),  # Step 5.2: the ordinary student
        ("student", "student", roles.STUDENT, None),
        ("Assistant Professor", "faculty", roles.FACULTY, None),
        ("faculty", None, roles.FACULTY, None),
        ("HOD (CSE)", "faculty", roles.HOD, "CSE"),
        ("HOD (Liberal Arts)", "faculty", roles.HOD, "LA"),
        ("deptadmin_sm", "staff", roles.DEPT_ADMIN, "SM"),
        ("acadadmin", "staff", roles.CENTRAL, None),
        ("dept_admin", "staff", None, None),  # no department named, so no grant (blueprint 4)
        ("Hostel_admin", "staff", None, None),
        ("staff", "staff", None, None),
        (None, "faculty", None, None),
    ],
)
def test_role_and_office_department_from_designation(active, kind, role, dept):
    assert roles.role_of(active, kind) == role
    assert roles.office_department(active) == dept


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("Des.", "Design"),
        ("Natural Science", "NS"),
        ("Liberal Arts", "LA"),
        (" CSE ", "CSE"),
        ("MT", None),
        ("", None),
        (None, None),
    ],
)
def test_erp_department_spellings_normalise(raw, code):
    assert roles.normalise_department(raw) == code


def test_every_designation_department_is_a_seeded_code():
    named = set(roles.HOD_DESIGNATIONS.values()) | set(roles.DEPT_ADMIN_DESIGNATIONS.values())
    assert named <= set(roles.DEPARTMENT_CODES)


def test_actor_context_is_office_only_with_a_department():
    assert ActorContext(1, roles.HOD, "CSE").is_office
    assert not ActorContext(1, roles.HOD, None).is_office
    assert not ActorContext(1, roles.FACULTY, "CSE").is_office


# -- announcements (BR-DEPT-002, BR-DEPT-003) ----------------------------------------
def test_br_dept_003_complete_announcement_passes():
    r.validate_announcement(title="t", body="b", audience_role="all")


@pytest.mark.parametrize(
    ("kw", "field"),
    [
        ({"title": " "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"body": ""}, "body"),
        ({"body": "x" * 5001}, "body"),
        ({"audience_role": "everyone"}, "audience_role"),
        ({"batch_year": 1990}, "batch_year"),
        ({"programme": "x" * 41}, "programme"),
    ],
)
def test_br_dept_003_missing_or_invalid_field_is_named(kw, field):
    base = {"title": "t", "body": "b", "audience_role": "all"}
    with pytest.raises(RuleViolation) as exc:
        r.validate_announcement(**{**base, **kw})
    assert exc.value.code == "announcement_incomplete"
    assert [d["field"] for d in exc.value.details] == [field]


# -- stock (BR-DEPT-015) -------------------------------------------------------------
def test_br_dept_015_enough_stock_passes_including_exactly_all_of_it():
    r.check_availability(requested=5, available=5)


@pytest.mark.parametrize(
    ("requested", "available", "code"),
    [(6, 5, "insufficient_stock"), (0, 5, "invalid_quantity"), (-1, 5, "invalid_quantity")],
)
def test_br_dept_015_refusals(requested, available, code):
    with pytest.raises(RuleViolation) as exc:
        r.check_availability(requested=requested, available=available)
    assert exc.value.code == code


def test_receipt_must_add_stock():
    r.check_receipt(1)
    with pytest.raises(RuleViolation):
        r.check_receipt(0)


# -- timetable (BR-DEPT-010, Q6) -------------------------------------------------------
def _slot(key, day=0, start=9, end=10, room="L1", prog="B.Tech", year=2024):
    return r.Slot(key, day, time(start), time(end), room, prog, year)


@pytest.mark.parametrize(
    ("other", "clash"),
    [
        (_slot("b", start=9, end=10, room="L2", prog="M.Tech"), False),  # different room and group
        (
            _slot("b", start=9, end=10, room="l1 ", prog="M.Tech"),
            True,
        ),  # same room, case-insensitive
        (_slot("b", start=9, end=10, room="L2"), True),  # same programme and batch
        (_slot("b", start=10, end=11), False),  # end-to-start touching
        (_slot("b", day=1), False),  # another day
        (_slot("b", room="", prog=""), False),  # nothing shared
        (_slot("b", room="L2", year=None), False),  # batch unknown is not the same group
    ],
)
def test_br_dept_010_overlap_definition(other, clash):
    assert bool(r.find_overlaps([_slot("a")], [other])) is clash


def test_br_dept_010_clash_inside_the_uploaded_batch_is_found():
    assert r.find_overlaps([_slot("a"), _slot("b")], []) == [("b", "a")]


def test_slot_validation():
    r.validate_slot(_slot("a"))
    with pytest.raises(RuleViolation):
        r.validate_slot(_slot("a", start=10, end=9))
    with pytest.raises(RuleViolation):
        r.validate_slot(_slot("a", day=7))


# -- official details (BR-DEPT-011, AFR-DEPT-053) -----------------------------------------
def test_br_dept_011_only_name_and_core_policies_are_official():
    r.validate_official_change("core_policies", "")
    with pytest.raises(RuleViolation) as exc:
        r.validate_official_change("headship", "x")  # AFR-DEPT-053: headship is never proposed
    assert exc.value.code == "not_official_field"
    with pytest.raises(RuleViolation):
        r.validate_official_change("name", " ")


def test_general_update_refuses_official_fields():
    r.check_general_update(["description"])
    with pytest.raises(RuleViolation) as exc:
        r.check_general_update(["description", "name"])
    assert exc.value.code == "official_field"


def test_feedback_category_is_optional_but_closed():
    r.check_category("")
    r.check_category("academic")
    with pytest.raises(RuleViolation):
        r.check_category("rant")


# -- tenures (BR-DEPT-022, BR-DEPT-023) -----------------------------------------------------
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _t(key, start_days, end_days, user=1):
    return r.Tenure(key, user, T0 + timedelta(days=start_days), T0 + timedelta(days=end_days))


def test_br_dept_023_interval_must_be_positive():
    r.validate_interval(T0, T0 + timedelta(seconds=1))
    with pytest.raises(RuleViolation):
        r.validate_interval(T0, T0)


@pytest.mark.parametrize(
    ("other", "overlaps"),
    [(_t(2, 10, 20), False), (_t(2, 9, 20), True), (_t(2, -5, 0), False), (_t(1, 2, 3), False)],
)
def test_br_dept_022_overlap(other, overlaps):
    assert bool(r.overlapping(_t(1, 0, 10), [other])) is overlaps


def test_q1_shortening_without_successor_is_refused():
    now = T0 + timedelta(days=1)
    current = _t(1, 0, 10)
    r.check_shortening(
        current=current, new_valid_to=T0 + timedelta(days=20), successors=[], now=now
    )  # extend
    r.check_shortening(
        current=current, new_valid_to=T0 + timedelta(days=5), successors=[_t(2, 5, 9)], now=now
    )
    with pytest.raises(RuleViolation) as exc:
        r.check_shortening(
            current=current, new_valid_to=T0 + timedelta(days=5), successors=[], now=now
        )
    assert exc.value.code == "would_leave_gap"
    r.check_shortening(
        current=current, new_valid_to=now, successors=[], now=now
    )  # not in the future


# -- profile tiers (BR-DEPT-019) ---------------------------------------------------------------
@pytest.mark.parametrize(
    ("viewer", "target", "tier", "in_my_course"),
    [
        (roles.HOD, "student", r.FULL, False),
        (roles.DEPT_ADMIN, "alumni", r.FULL, False),
        (roles.FACULTY, "student", r.BASIC, False),
        (roles.FACULTY, "student", r.DETAILED, True),
        (roles.FACULTY, "faculty", r.LIMITED, True),
        (roles.STUDENT, "student", r.BASIC, True),
        (roles.FACULTY, "faculty", r.LIMITED, False),
        (roles.FACULTY, "alumni", r.LIMITED, False),
        (roles.STUDENT, "student", r.BASIC, False),
        (roles.STUDENT, "faculty", r.BASIC, False),
        (roles.STUDENT, "alumni", None, False),
        (roles.CENTRAL, "faculty", None, False),
        (None, "faculty", None, False),
    ],
)
def test_br_dept_019_tiers(viewer, target, tier, in_my_course):
    assert r.tier_for(viewer, target, in_my_course) == tier


def test_br_dept_019_tiers_only_grow_and_never_carry_sensitive_fields():
    tiers = [set(r.TIER_FIELDS[t]) for t in (r.BASIC, r.LIMITED, r.DETAILED, r.FULL)]
    assert all(a < b for a, b in pairwise(tiers))
    sensitive = {"date_of_birth", "phone", "address", "category", "gender", "medical"}
    assert not sensitive & set(r.TIER_FIELDS[r.FULL])


# -- state machines, exhaustively (Step 5.4) ------------------------------------------------------
@pytest.mark.parametrize("machine", sorted(sm.MACHINES))
def test_every_unlisted_move_is_refused(machine):
    table = {(t.frm, t.to): t for t in sm.MACHINES[machine]}
    states = sm.states(machine)
    for frm, to in product(states, states):
        for actor in ALL_ACTORS:
            t = table.get((frm, to))
            if t is None:
                with pytest.raises(InvalidTransition):
                    sm.resolve(machine, frm, to, actor)
            elif actor not in t.actors:
                with pytest.raises(ActorNotAllowed):
                    sm.resolve(machine, frm, to, actor)
            else:
                assert sm.resolve(machine, frm, to, actor) is t


def test_cw_dept_01_stock_lifecycle_table():
    # BW-DEPT-01, BW-DEPT-02, CW-DEPT-01; BR-DEPT-005, BR-DEPT-006, BR-DEPT-007
    assert {(t.frm, t.to, *t.actors) for t in sm.STOCK_TRANSITIONS} == {
        ("", "pending_hod", roles.FACULTY),
        ("pending_hod", "approved", roles.HOD),
        ("pending_hod", "rejected", roles.HOD),
        ("approved", "issued", roles.DEPT_ADMIN),
    }
    assert sm.terminal("stock request") == {"rejected", "issued"}


def test_cw_dept_02_feedback_lifecycle_table():
    # BW-DEPT-03, BW-DEPT-04, CW-DEPT-02; BR-DEPT-008, BR-DEPT-009, BR-DEPT-018
    from_new = [t for t in sm.FEEDBACK_TRANSITIONS if t.frm == "new"]
    assert [(t.to, t.actors) for t in from_new] == [("under_review", frozenset({roles.DEPT_ADMIN}))]
    assert sm.terminal("feedback") == {"resolved", "closed"}


def test_cw_dept_03_official_change_table():
    # BW-DEPT-05, BW-DEPT-06, CW-DEPT-03; BR-DEPT-011, BR-DEPT-013
    decisions = {t.to: t.actors for t in sm.OFFICIAL_CHANGE_TRANSITIONS if t.frm == "pending"}
    assert decisions == {"approved": frozenset({roles.HOD}), "rejected": frozenset({roles.HOD})}


def test_every_transition_permission_is_declared():
    from modules.department.registry import PERMISSIONS

    declared = {code for code, _ in PERMISSIONS}
    assert {t.permission for table in sm.MACHINES.values() for t in table} <= declared
