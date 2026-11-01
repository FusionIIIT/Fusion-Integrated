import datetime

def window_is_open(status, opens_on, closes_on, today):
    if status == 'OPEN' and opens_on <= today <= closes_on:
        return True
    return False

def deregistration_effective_date(approved_on):
    next_day = approved_on + datetime.timedelta(days=1)
    return next_day

def validate_window(title, opens_on, closes_on):
    errors = []
    if not title.strip():
        errors.append('Title must be non-blank')
    if opens_on is None or closes_on is None:
        errors.append('Both dates required')
    if closes_on < opens_on:
        errors.append('Closes_on must not be before opens_on')
    return errors
