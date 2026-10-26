from datetime import date


def validate_leave_request(
    leave_category: str,
    start_date: date,
    end_date: date,
    is_half_day: bool,
    current_balance: float,
    existing_leaves: list[dict],
    half: str | None = None
) -> tuple[bool, str]:
    # BR-EL-001: Category validation
    valid_categories = {'CL', 'RH', 'SCL', 'EL', 'COL', 'VL'}
    if leave_category not in valid_categories:
        return False, "Invalid leave category"

    # Date range validation
    if start_date > end_date:
        return False, "Invalid date range"

    # BR-EL-010: Half-day CL consumes 0.5 day
    requested = 0.5 if is_half_day else (end_date - start_date).days + 1

    # Balance check
    if requested > current_balance:
        return False, "Insufficient leave balance"

    # BR-EL-012: Overlap check with half-day CL exception
    for leave in existing_leaves:
        if leave['status'] not in ['pending', 'approved']:
            continue

        existing_start = leave['start_date']
        existing_end = leave['end_date']
        existing_is_half_day = leave.get('is_half_day', False)
        existing_half = leave.get('half')  # 'first' or 'second' or None

        # Check if date ranges overlap
        ranges_overlap = (start_date <= existing_end and end_date >= existing_start)

        if not ranges_overlap:
            continue

        # BR-EL-012 exception: first-half and second-half CL on same date are allowed
        if ((leave_category == 'CL' and
            existing_is_half_day and is_half_day and
            start_date == existing_start == existing_end and
            ((existing_half == 'first' and half == 'second'))) or
            (existing_half == 'second' and half == 'first')):
            continue  # Different halves, no overlap

        return False, "Overlap with existing leave"

    return True, ""
