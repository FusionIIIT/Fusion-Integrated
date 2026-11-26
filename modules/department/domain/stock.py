class IllegalTransition(Exception):
    pass

TRANSITIONS = {
    ("pending_hod_approval", "approve", "hod"): "approved_for_issuance",
    ("pending_hod_approval", "reject", "hod"): "rejected",
    ("approved_for_issuance", "issue", "dept_admin"): "issued",
}

def next_state(state, event, role_kind):
    transition = (state, event, role_kind)
    if transition in TRANSITIONS:
        return TRANSITIONS[transition]
    raise IllegalTransition(f"Invalid transition: {state} with event {event} by role {role_kind}")
