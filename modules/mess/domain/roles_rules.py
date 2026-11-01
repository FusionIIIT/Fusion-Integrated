def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end < b_start or b_end < a_start)

def can_assign(role, new_start, new_end, existing):
    for existing_role, existing_start, existing_end in existing:
        if existing_role == role and overlaps(new_start, new_end, existing_start, existing_end):
            return False
    return True

def is_active(start, end, now):
    return start <= now < end
