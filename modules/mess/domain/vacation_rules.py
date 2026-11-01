VALID_RESPONSES = ('YES', 'NO')

def validate_response(value):
    if value.upper() not in VALID_RESPONSES:
        raise ValueError("Invalid response")
    return value.upper()

def resolve_response(explicit, deadline_passed):
    if explicit is not None:
        return explicit
    elif deadline_passed:
        return 'NO'
    else:
        return None
