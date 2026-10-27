import pytest

from modules.leave.domain import state_machine as sm

# --- Test Fixtures and Setup ---

# Define states for easier testing
STATES = {
    "awaiting_substitute", "applicant_action_required", "awaiting_unit_head",
    "awaiting_establishment", "awaiting_final_sanction", "awaiting_director_self_sanction",
    "approved", "rejected", "withdrawn", "cancellation_pending_unit_head",
    "cancellation_pending_establishment", "cancellation_pending_final", "cancelled"
}

# Define actors
ACTORS = {
    "employee", "substitute", "unit_head", "establishment", "authority", "director", "system"
}

# Define category codes
CATEGORIES = {
    "CL", "RH", "SCL", "EL", "COL", "VL"
}

# --- Test initial_state (Requirement 1) ---

@pytest.mark.parametrize(
    "sub_req, dir_app, expected",
    [
        (True, False, "awaiting_substitute"),
        (True, True, "awaiting_substitute"),
        (False, True, "awaiting_director_self_sanction"),
        (False, False, "awaiting_unit_head"),
    ],
)
def test_initial_state(sub_req, dir_app, expected):
    """Tests the initial state determination based on requirements."""
    assert sm.initial_state(sub_req, dir_app) == expected

# --- Test Transition Resolution (Requirements 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13) ---

def test_cl_rh_happy_path():
    """Tests CL/RH happy path (BW-EL-01)."""
    # awaiting_unit_head -> approved by unit_head (CL)
    t1 = sm.resolve("awaiting_unit_head", "approved", "unit_head", "CL")
    assert t1.permission == "leave_management.application.review"
    assert t1.scope == "unit_head_final"

    # awaiting_unit_head -> rejected by unit_head (RH)
    t2 = sm.resolve("awaiting_unit_head", "rejected", "unit_head", "RH")
    assert t2.permission == "leave_management.application.review"
    assert t2.scope == "unit_head_final"

def test_scope_mismatch_unit_head():
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

def test_substitute_loop():
    """Tests Substitute loop (BW-EL-03) (Requirement 4)."""
    # 1. awaiting_substitute -> applicant_action_required (substitute)
    t1 = sm.resolve("awaiting_substitute", "applicant_action_required", "substitute")
    assert t1.permission == "leave_management.application.respond"

    # 2. applicant_action_required -> awaiting_substitute (employee)
    t2 = sm.resolve("applicant_action_required", "awaiting_substitute", "employee")
    assert t2.permission == "leave_management.application.create"

    # 3. awaiting_substitute -> awaiting_unit_head (substitute)
    t3 = sm.resolve("awaiting_substitute", "awaiting_unit_head", "substitute")
    assert t3.permission == "leave_management.application.respond"

def test_director_path():
    """Tests Director path (Requirement 5)."""
    # 1. awaiting_substitute -> awaiting_director_self_sanction by substitute
    t1 = sm.resolve("awaiting_substitute", "awaiting_director_self_sanction", "substitute")
    assert t1.permission == "leave_management.application.respond"

    # 2. awaiting_director_self_sanction -> approved by director
    t2 = sm.resolve("awaiting_director_self_sanction", "approved", "director")
    assert t2.permission == "leave_management.application.review"

    # 3. awaiting_director_self_sanction -> rejected by director
    t3 = sm.resolve("awaiting_director_self_sanction", "rejected", "director")
    assert t3.permission == "leave_management.application.review"

    # 4. Unit_head trying to move director state (ActorNotAllowed)
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("awaiting_director_self_sanction", "approved", "unit_head")

def test_higher_sanction_route():
    """Tests Higher-sanction route (BW-EL-04) (Requirement 6)."""
    # 1. unit_head -> awaiting_establishment
    t1 = sm.resolve("awaiting_unit_head", "awaiting_establishment", "unit_head", "EL")
    assert t1.permission == "leave_management.application.review"
    assert t1.scope == "higher"

    # 2. establishment -> awaiting_final_sanction
    t2 = sm.resolve("awaiting_establishment", "awaiting_final_sanction", "establishment")
    assert t2.permission == "leave_management.application.review"
    assert t2.scope == "higher"

    # 3. authority -> approved
    t3 = sm.resolve("awaiting_final_sanction", "approved", "authority")
    assert t3.permission == "leave_management.application.review"
    assert t3.scope == "higher"

    # 4. authority -> rejected
    t4 = sm.resolve("awaiting_final_sanction", "rejected", "authority")
    assert t4.permission == "leave_management.application.review"
    assert t4.scope == "higher"

def test_wrong_actors():
    """Tests wrong actors for transitions (Requirement 7)."""
    # Employee cannot approve (awaiting_unit_head -> approved)
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("awaiting_unit_head", "approved", "employee")

    # Unit_head cannot move awaiting_final_sanction -> approved
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("awaiting_final_sanction", "approved", "unit_head")

    # Employee cannot move awaiting_substitute -> awaiting_unit_head
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("awaiting_substitute", "awaiting_unit_head", "employee")

def test_withdrawal():
    """Tests withdrawal functionality (Requirement 8)."""
    pending_states = {
        "awaiting_substitute", "applicant_action_required", "awaiting_unit_head",
        "awaiting_establishment", "awaiting_final_sanction", "awaiting_director_self_sanction"
    }

    # Check withdrawal for all pending states by employee
    for state in pending_states:
        t = sm.resolve(state, "withdrawn", "employee")
        assert t.permission == "leave_management.application.delete"

    # Unit_head withdrawing (should fail)
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("awaiting_unit_head", "withdrawn", "unit_head")

def test_illegal_transitions():
    """Tests illegal transitions (Requirement 9)."""
    # Terminal states have no outgoing edges (tested later, but check specific illegal moves here)

    # Withdrawing from approved (Illegal)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve("approved", "withdrawn", "employee")

    # Withdrawing from cancellation_pending_unit_head (Illegal)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve("cancellation_pending_unit_head", "withdrawn", "employee")

    # Approved -> Rejected (Illegal)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve("approved", "rejected", "employee")

    # awaiting_substitute -> awaiting_final_sanction (Illegal skip)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve("awaiting_substitute", "awaiting_final_sanction", "substitute")

def test_cancellation_flow():
    """Tests Cancellation flow (CW-EL-02) (Requirement 11)."""
    # 1. approved -> cancellation_pending_unit_head by employee
    t1 = sm.resolve("approved", "cancellation_pending_unit_head", "employee")
    assert t1.permission == "leave_management.application.create"

    # 2. unit_head cancellation_pending_unit_head -> cancelled
    t2 = sm.resolve("cancellation_pending_unit_head", "cancelled", "unit_head", "CL")
    assert t2.scope == "unit_head_final"

    # 3. unit_head cancellation_pending_unit_head -> approved (CL)
    t3 = sm.resolve("cancellation_pending_unit_head", "approved", "unit_head", "CL")
    assert t3.scope == "unit_head_final"

    # 4. unit_head cancellation_pending_unit_head -> cancellation_pending_establishment (higher)
    t4 = sm.resolve("cancellation_pending_unit_head", "cancellation_pending_establishment", "unit_head", "EL")
    assert t4.scope == "higher"

    # 5. establishment -> cancellation_pending_final
    t5 = sm.resolve("cancellation_pending_establishment", "cancellation_pending_final", "establishment")
    assert t5.scope == "higher"

    # 6. authority cancellation_pending_final -> cancelled
    t6 = sm.resolve("cancellation_pending_final", "cancelled", "authority")
    assert t6.scope == "higher"

    # 7. authority cancellation_pending_final -> approved
    t7 = sm.resolve("cancellation_pending_final", "approved", "authority")
    assert t7.scope == "higher"

def test_cancellation_scope_by_category():
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("cancellation_pending_unit_head", "cancelled", "unit_head", "VL")
    with pytest.raises(sm.ScopeMismatch):
        sm.resolve("cancellation_pending_unit_head", "approved", "unit_head", "VL")
    t = sm.resolve("cancellation_pending_unit_head", "cancellation_pending_final", "unit_head", "VL")
    assert t.scope == "higher"

# --- Test Integrity and Properties (Requirements 10, 12, 13) ---

def test_terminal_states_no_outgoing_edges():
    """Tests that terminal states have no outgoing edges (Requirement 10)."""
    terminal_states = sm.TERMINAL
    for state in terminal_states:
        assert sm.allowed_targets(state) == []

def test_permission_mapping():
    """Tests specific permission mappings (Requirement 12)."""
    # awaiting_unit_head -> approved
    t1 = sm.resolve("awaiting_unit_head", "approved", "unit_head", "CL")
    assert t1.permission == "leave_management.application.review"

    # approved -> cancellation_pending_unit_head
    t2 = sm.resolve("approved", "cancellation_pending_unit_head", "employee")
    assert t2.permission == "leave_management.application.create"

    # awaiting_substitute -> awaiting_unit_head
    t3 = sm.resolve("awaiting_substitute", "awaiting_unit_head", "substitute")
    assert t3.permission == "leave_management.application.respond"

def test_table_integrity_and_targets():
    """Tests table integrity and allowed targets (Requirement 13)."""

    # Check allowed targets for awaiting_unit_head
    expected_targets = sorted([
        "approved", "awaiting_establishment", "awaiting_final_sanction", "rejected"
    ])
    assert sm.allowed_targets("awaiting_unit_head", "unit_head") == expected_targets

    # Check table integrity: all states must be defined
    all_defined_states = set()
    for t in sm.TRANSITIONS:
        all_defined_states.add(t.frm)
        all_defined_states.add(t.to)

    assert all_defined_states == STATES

    # Check no two transitions share the same (frm, to)
    transitions_map = {}
    for t in sm.TRANSITIONS:
        key = (t.frm, t.to)
        assert key not in transitions_map, f"Duplicate transition found for {key}"
        transitions_map[key] = t

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
