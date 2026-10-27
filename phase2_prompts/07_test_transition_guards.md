# Task: add tests for transition guards to modules/leave/tests/test_state_machine.py (output the COMPLETE file)

In `modules/leave/tests/test_state_machine.py`, keep ALL existing test functions exactly as they are, and append this new test function at the end:

def test_transition_guards_present():
    """Verify has_reason and before_start_date guards on required transitions (gap a)."""
    # Rejections require has_reason
    t_uh_reject = sm.resolve("awaiting_unit_head", "rejected", "unit_head", "CL")
    assert "has_reason" in t_uh_reject.guards

    t_auth_reject = sm.resolve("awaiting_final_sanction", "rejected", "authority", "EL")
    assert "has_reason" in t_auth_reject.guards

    t_dir_reject = sm.resolve("awaiting_director_self_sanction", "rejected", "director")
    assert "has_reason" in t_dir_reject.guards

    # Cancellation rejection (stay approved) requires has_reason
    t_uh_canc_reject = sm.resolve("cancellation_pending_unit_head", "approved", "unit_head", "CL")
    assert "has_reason" in t_uh_canc_reject.guards

    t_auth_canc_reject = sm.resolve("cancellation_pending_final", "approved", "authority", "VL")
    assert "has_reason" in t_auth_canc_reject.guards

    # Cancellation initiation requires before_start_date
    t_cancel = sm.resolve("approved", "cancellation_pending_unit_head", "employee")
    assert "before_start_date" in t_cancel.guards

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
