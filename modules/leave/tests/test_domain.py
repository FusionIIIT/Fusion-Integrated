"""Domain tests: pure Python, no database."""
import pytest

from modules.leave.domain import entitlement as ent
from modules.leave.domain import state_machine as sm


def test_table_is_spec():
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm, to in declared:
        assert sm.is_legal(frm, to) is True


def test_illegal_raises():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.DRAFT, sm.APPROVED)


def test_terminal_have_no_exits():
    for s in (sm.REJECTED, sm.WITHDRAWN, sm.CANCELLED):
        assert sm.allowed_targets(s) == []
    assert sm.allowed_targets(sm.APPROVED) == [sm.CANCELLED]



def test_entitlement_values():
    assert ent.yearly_credit("CL") == 8
    assert ent.yearly_credit("RH") == 2
    assert ent.yearly_credit("EL") == 30
    assert ent.carries_forward("EL") is True
    assert ent.carries_forward("CL") is False
    assert ent.vl_to_el(60) == 30.0
