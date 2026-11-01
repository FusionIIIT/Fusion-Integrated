import datetime

REASONS = ['medical', 'institute_leave', 'family_function', 'other']
MIN_DAYS = 3

def validate_rebate(reason, explanation, start_date, end_date, submitted_on, existing_ranges):
    errors = []

    if reason not in REASONS:
        errors.append('Invalid reason')

    if reason == 'other' and not explanation:
        errors.append('Explanation must be non-blank when reason is other')

    if end_date < start_date:
        errors.append('End date must not be before start date')

    if (end_date - start_date).days < MIN_DAYS:
        errors.append('Duration counting both ends must be at least {} days'.format(MIN_DAYS))

    if submitted_on < start_date - datetime.timedelta(days=1):
        errors.append('Submitted on must be at least 1 calendar day before start date')

    for existing_range in existing_ranges:
        if start_date <= existing_range[1] and end_date >= existing_range[0]:
            errors.append('Range must not overlap any existing range')

    return errors

def rebate_days_in_month(start, end, year, month):
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, -1)
    total_days = (end_date - start_date).days + 1
    days_in_month = (end_date - start_date).days
    days_in_range = sum(max(0, end_date.day - existing_range[1].day) + max(0, existing_range[0].day - start_date.day) for existing_range in existing_ranges)
    return total_days - days_in_month - days_in_range
