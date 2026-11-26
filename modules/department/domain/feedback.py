class IllegalTransition(Exception):
    pass

TRANSITIONS = {
    ("new", "review", "dept_admin"): "under_review",
    ("under_review", "resolve", "dept_admin"): "resolved",
    ("under_review", "close", "dept_admin"): "closed",
    ("under_review", "resolve", "hod"): "resolved",
    ("under_review", "close", "hod"): "closed",
}

def next_state(state, event, role_kind):
    transition_key = (state, event, role_kind)
    if transition_key in TRANSITIONS:
        return TRANSITIONS[transition_key]
    raise IllegalTransition(f"Invalid transition from {state} with event {event} by role {role_kind}")
