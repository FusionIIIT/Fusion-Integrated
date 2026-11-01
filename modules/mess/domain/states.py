# Define the dictionaries
allowed_status_transitions = {
    'REGISTRATION': {'PENDING': ['APPROVED', 'REJECTED']},
    'DEREGISTRATION': {'PENDING': ['APPROVED_AWAITING_EFFECTIVE', 'REJECTED']},
    'APPROVED_AWAITING_EFFECTIVE': {'APPROVED', 'REJECTED'},
    'REBATE': {'PENDING': ['APPROVED', 'REJECTED']},
    'SPECIAL_FOOD': {'REQUESTED': ['APPROVED', 'REJECTED']},
    'BILL': {'GENERATED': 'FINALIZED'},
    'FINALIZED': {'PUBLISHED': 'PUBLISHED'},
    'VACATION_SURVEY': {'OPEN': 'CLOSED'}
}

def can_transition(machine, old, new):
    if machine not in allowed_status_transitions:
        return False
    if old not in allowed_status_transitions[machine]:
        return False
    if new not in allowed_status_transitions[machine][old]:
        return False
    return True

def allowed_next(machine, old):
    if machine not in allowed_status_transitions:
        return []
    if old not in allowed_status_transitions[machine]:
        return []
    return sorted(allowed_status_transitions[machine][old])
