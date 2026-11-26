class IllegalTransition(Exception):
    pass

OFFICIAL_FIELDS = frozenset(["name", "core_policies"])
GENERAL_FIELDS = frozenset(["about", "contact_email", "location", "website"])

TRANSITIONS = {
    ("pending_hod_approval", "approve"): "approved",
    ("pending_hod_approval", "reject"): "rejected",
}

def split_changes(data):
    """
    Splits data into official and general dictionaries, keeping only known keys.
    Raises ValueError if data contains 'headship'.
    """
    if "headship" in data:
        raise ValueError("Headship field is not allowed in changes.")

    official_dict = {}
    general_dict = {}

    for key, value in data.items():
        if key in OFFICIAL_FIELDS:
            official_dict[key] = value
        elif key in GENERAL_FIELDS:
            general_dict[key] = value
        # Ignore unknown keys

    return official_dict, general_dict

def next_state(state, event):
    """
    Returns the next state based on the current state and event,
    or raises IllegalTransition if the transition is invalid.
    """
    transition_key = (state, event)
    if transition_key in TRANSITIONS:
        return TRANSITIONS[transition_key]
    raise IllegalTransition(f"Invalid transition from state '{state}' with event '{event}'")
