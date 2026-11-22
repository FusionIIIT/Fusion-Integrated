import pytest

from modules.vms.domain import extension_state as ex
from modules.vms.domain import muster_state as mu


def test_muster_open_to_closed():
    assert mu.resolve(mu.OPEN, mu.CLOSE) == mu.CLOSED


def test_muster_closed_is_final():
    with pytest.raises(mu.InvalidTransition):
        mu.resolve(mu.CLOSED, mu.CLOSE)


def test_muster_entry_moves():
    assert mu.resolve_entry(mu.UNACCOUNTED, mu.MARK_ACCOUNTED) == mu.ACCOUNTED
    assert mu.resolve_entry(mu.UNACCOUNTED, mu.MARK_EVACUATED) == mu.EVACUATED
    for s in (mu.ACCOUNTED, mu.EVACUATED):
        with pytest.raises(mu.InvalidTransition):
            mu.resolve_entry(s, mu.MARK_ACCOUNTED)


@pytest.mark.parametrize("event,to", [(ex.APPROVE, ex.APPROVED), (ex.REJECT, ex.REJECTED)])
def test_extension_pending_decisions(event, to):
    assert ex.resolve(ex.PENDING, event) == to


@pytest.mark.parametrize("state", sorted(ex.TERMINAL))
@pytest.mark.parametrize("event", [ex.APPROVE, ex.REJECT])
def test_extension_terminal_states_are_final(state, event):
    with pytest.raises(ex.InvalidTransition):
        ex.resolve(state, event)
