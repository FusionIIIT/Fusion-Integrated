"""Every illegal move is refused, enumerated from the table (Step 5.4)."""
import inspect
from itertools import product

import pytest

from modules.elm import registry
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveApplication
from modules.elm.services import applications as service

STATUSES = sorted(sm.ALL_STATUSES)
LEGAL = {(t.frm, t.to) for t in sm.TRANSITIONS}


class TestTheTable:

    def test_every_legal_pair_resolves(self):
        for frm, to in sorted(LEGAL):
            assert sm.is_legal(frm, to)

    def test_every_other_pair_is_illegal(self):
        for frm, to in product(STATUSES, STATUSES):
            if (frm, to) in LEGAL:
                continue
            with pytest.raises(sm.InvalidTransition):
                sm.resolve(frm, to)

    def test_terminal_states_have_no_exits(self):
        for terminal in sorted(sm.TERMINAL):
            assert sm.allowed_targets(terminal) == []

    def test_an_employee_cannot_approve(self):
        with pytest.raises(sm.ActorNotAllowed):
            sm.resolve(sm.PENDING, sm.APPROVED, sm.EMPLOYEE)

    def test_an_approver_cannot_withdraw_someone_elses_request(self):
        with pytest.raises(sm.ActorNotAllowed):
            sm.resolve(sm.PENDING, sm.WITHDRAWN, sm.APPROVER)

    def test_the_system_cannot_decide(self):
        with pytest.raises(sm.ActorNotAllowed):
            sm.resolve(sm.PENDING, sm.APPROVED, sm.SYSTEM)

    def test_allowed_targets_are_lane_specific(self):
        assert sm.allowed_targets(sm.PENDING, sm.EMPLOYEE) == ["withdrawn"]
        assert sm.allowed_targets(sm.PENDING, sm.APPROVER) == ["approved",
                                                               "rejected"]
        assert sm.allowed_targets(sm.APPROVED, sm.EMPLOYEE) == ["cancelled"]


class TestDrift:

    def test_every_transition_permission_is_declared_in_the_registry(self):
        declared = {code for code, _ in registry.PERMISSIONS}
        for transition in sm.TRANSITIONS:
            assert transition.permission in declared

    def test_every_guard_name_is_implemented_by_the_service(self):
        source = inspect.getsource(service._run_guards)
        guards = {g for t in sm.TRANSITIONS for g in t.guards}
        assert guards
        for guard in sorted(guards):
            assert f'"{guard}"' in source

    def test_the_model_and_the_machine_agree_on_statuses(self):
        assert {s for s, _ in LeaveApplication.STATUS} == set(sm.ALL_STATUSES)
