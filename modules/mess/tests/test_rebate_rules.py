from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def validate_rebate(reason, explanation, start_date, end_date, submitted_on, existing_ranges):
    errors = []

    if reason == "other":
        if explanation == "":
            errors.append("Explanation cannot be empty")
        else:
            errors.append("Explanation is valid")
    else:
        errors.append("Unknown reason")

    if submitted_on == start_date:
        errors.append("Submitted on the same day as start")
    elif submitted_on == start_date - timedelta(days=1):
        errors.append("Submitted exactly 1 day before start")
    elif submitted_on == start_date + timedelta(days=1):
        errors.append("Submitted 2 days early")
    else:
        errors.append("Invalid date")

    if existing_ranges is not None:
        for range in existing_ranges:
            if range[0] <= submitted_on <= range[1]:
                errors.append("Overlapping existing range")

    return errors
