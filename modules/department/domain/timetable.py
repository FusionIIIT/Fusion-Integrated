
Slot = dict[str, any]

def overlaps(a: Slot, b: Slot) -> bool:
    """
    Checks if two slots overlap.
    Slots overlap if they are on the same weekday and their time ranges intersect.
    Adjoining slots do not overlap.
    """
    if a.get('weekday') != b.get('weekday'):
        return False

    start_a = a.get('start_time')
    end_a = a.get('end_time')
    start_b = b.get('start_time')
    end_b = b.get('end_time')

    # Check for overlap: a starts before b ends AND b starts before a ends
    return start_a < end_b and start_b < end_a

def conflicts(a: Slot, b: Slot) -> bool:
    """
    Checks if two slots conflict.
    Conflicts occur if they overlap AND share a resource (room, faculty_user_id, or programme/batch_year).
    """
    if not overlaps(a, b):
        return False

    # Check for shared room
    room_a = a.get('room')
    room_b = b.get('room')
    if room_a is not None and room_b is not None and room_a == room_b:
        return True

    # Check for shared faculty_user_id
    faculty_a = a.get('faculty_user_id')
    faculty_b = b.get('faculty_user_id')
    if faculty_a is not None and faculty_b is not None and faculty_a == faculty_b:
        return True

    # Check for shared programme and batch_year
    programme_a = a.get('programme')
    batch_year_a = a.get('batch_year')
    programme_b = b.get('programme')
    batch_year_b = b.get('batch_year')

    if (programme_a is not None and programme_b is not None and programme_a == programme_b and
            batch_year_a is not None and batch_year_b is not None and batch_year_a == batch_year_b):
        return True

    return False

def find_conflicts(candidates: list[Slot], existing: list[Slot]) -> list[tuple[Slot, Slot]]:
    """
    Finds all conflict pairs.
    Checks each candidate against every existing slot and against the other candidates.
    Never checks a slot against one with the same non-None id.
    """
    conflicts_list: list[tuple[Slot, Slot]] = []

    # 1. Check candidates against existing slots
    for candidate in candidates:
        for existing_slot in existing:
            # Skip if they are the same slot (assuming id is the unique identifier)
            if candidate.get('id') == existing_slot.get('id'):
                continue

            if conflicts(candidate, existing_slot):
                conflicts_list.append((candidate, existing_slot))

    # 2. Check candidates against each other
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            candidate_a = candidates[i]
            candidate_b = candidates[j]

            # Skip if they are the same slot (shouldn't happen if candidates are unique, but safe check)
            if candidate_a.get('id') == candidate_b.get('id'):
                continue

            if conflicts(candidate_a, candidate_b):
                conflicts_list.append((candidate_a, candidate_b))

    return conflicts_list
