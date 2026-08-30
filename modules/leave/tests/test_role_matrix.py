"""Who gets what, asserted rather than assumed.

The grant map is the whole of ELM's authorization surface, and it is a dict
literal -- nothing else in the module can tell you it is wrong. Two mistakes
lived in it: no grant for the basic roles IAM gives every employee, so most of
the institute could not apply at all; and review plus the balance directory
attached to "Professor", which is a chair rather than an office.
"""
import pytest

from modules.leave import registry

DECLARED = {code for code, _ in registry.PERMISSIONS}

EMPLOYEE = {
    "leave.request.create", "leave.request.view_self", "leave.request.withdraw",
    "leave.substitute.respond",
}
PRIVILEGED = {
    "leave.request.review", "leave.request.route", "leave.request.sanction",
    "leave.resumption.verify", "leave.balance.view", "leave.policy.manage",
    "leave.calendar.manage", "leave.offline.record",
}


def granted(role: str) -> set[str]:
    return set(registry.ROLE_GRANTS.get(role, ()))


class TestEveryEmployeeCanApply:
    @pytest.mark.parametrize("basic", ["faculty", "staff"])
    def test_the_basic_role_carries_the_employee_permissions(self, basic):
        # IAM injects this role for every employee, designation or not.
        assert granted(basic) >= EMPLOYEE

    @pytest.mark.parametrize("basic", ["faculty", "staff"])
    def test_the_basic_role_carries_nothing_privileged(self, basic):
        assert granted(basic) & PRIVILEGED == set()

    def test_students_get_nothing(self):
        # ELM is Employee Leave Management.
        assert granted("student") == set()

    def test_an_unclassified_account_gets_nothing(self):
        assert granted("unknown") == set()


class TestPrivilegeSitsWithOfficesNotRanks:
    @pytest.mark.parametrize(
        "rank", ["Professor", "Associate Professor", "Assistant Professor"])
    def test_an_academic_rank_is_only_an_employee(self, rank):
        assert granted(rank) == EMPLOYEE

    @pytest.mark.parametrize("hod", [
        "HOD (CSE)", "HOD (ECE)", "HOD (ME)", "HOD (Design)", "HOD (NS)",
        "HOD (Liberal Arts)"])
    def test_a_head_of_department_reviews(self, hod):
        assert "leave.request.review" in granted(hod)
        assert "leave.request.sanction" not in granted(hod)

    def test_the_establishment_routes_and_verifies_but_does_not_sanction(self):
        for role in ("Deputy Registrar", "dracad"):
            assert "leave.request.route" in granted(role)
            assert "leave.resumption.verify" in granted(role)
            assert "leave.request.sanction" not in granted(role)

    def test_only_the_authorities_sanction(self):
        sanctioners = {r for r in registry.ROLE_GRANTS
                       if "leave.request.sanction" in granted(r)}
        assert sanctioners == {
            "Registrar", "Dean Academic", "Dean (R&D)", "Dean (P&D)", "Dean_s",
            "Director"}

    def test_only_the_administrator_maintains_policy(self):
        managers = {r for r in registry.ROLE_GRANTS
                    if "leave.policy.manage" in granted(r)}
        assert managers == {"acadadmin"}


class TestTheMapIsInternallyConsistent:
    def test_every_granted_permission_is_declared(self):
        for role, codes in registry.ROLE_GRANTS.items():
            unknown = set(codes) - DECLARED
            assert not unknown, f"{role} granted undeclared {unknown}"

    def test_no_role_is_granted_the_same_permission_twice(self):
        for role, codes in registry.ROLE_GRANTS.items():
            assert len(codes) == len(set(codes)), f"{role} has duplicates"

    def test_every_declared_permission_reaches_somebody(self):
        reachable = {c for codes in registry.ROLE_GRANTS.values() for c in codes}
        assert DECLARED - reachable == set()
