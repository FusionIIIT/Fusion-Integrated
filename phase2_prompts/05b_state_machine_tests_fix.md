# Task: fix two problems in modules/leave/tests/test_state_machine.py (output the COMPLETE file; all other tests unchanged)

1. `test_scope_mismatch_unit_head` is self-contradictory (it expects the same call to raise ScopeMismatch AND to succeed). Replace the whole test with:

def test_scope_mismatch_unit_head(sm):
    """Unit Head final approval is only for CL/RH (BR-EL-016); higher-sanction goes to recommendation (BR-EL-017)."""
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("awaiting_unit_head", "approved", "unit_head", "EL")
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("awaiting_unit_head", "rejected", "unit_head", "SCL")
    t_ok = sm.resolve("awaiting_unit_head", "awaiting_final_sanction", "unit_head", "EL")
    assert t_ok.scope == "higher"
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("awaiting_unit_head", "awaiting_final_sanction", "unit_head", "CL")
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("awaiting_final_sanction", "approved", "authority", "CL")

2. Append this new test (cancellation scope, requirement 11) at the end of the cancellation section:

def test_cancellation_scope_by_category(sm):
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("cancellation_pending_unit_head", "cancelled", "unit_head", "VL")
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("cancellation_pending_unit_head", "approved", "unit_head", "VL")
    t = sm.resolve("cancellation_pending_unit_head", "cancellation_pending_final", "unit_head", "VL")
    assert t.scope == "higher"

Output the COMPLETE file only. Blank lines must be completely empty. No explanations, no placeholders, no TODOs.
