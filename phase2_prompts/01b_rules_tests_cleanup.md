# Task: small cleanup of modules/leave/tests/test_rules.py (complete file output)

Keep every test exactly as it is EXCEPT these changes:
1. Delete the unused `today` fixture.
2. Replace `test_check_overlap_touching_end_start_true` with this clean version (no scratch comments, no dead code):

def test_check_overlap_touching_end_start_true():
    existing = [(date(2024, 1, 1), date(2024, 1, 5), None)]
    # new request starts on the last day of the existing one (ends are inclusive)
    assert rules.check_overlap(existing, date(2024, 1, 5), date(2024, 1, 10)) is True
    # new request ends on the first day of the existing one
    assert rules.check_overlap(existing, date(2023, 12, 28), date(2024, 1, 1)) is True

3. Add these two tests at the end of the Overlap section:

def test_check_overlap_second_half_vs_first_half_existing_no_overlap():
    day = date(2024, 1, 1)
    assert rules.check_overlap([(day, day, "second")], day, day, new_half="first") is False

def test_check_overlap_checks_every_existing_leave():
    existing = [(date(2024, 1, 1), date(2024, 1, 2), None), (date(2024, 2, 1), date(2024, 2, 5), None)]
    assert rules.check_overlap(existing, date(2024, 2, 3), date(2024, 2, 3)) is True

Output the COMPLETE file only. No explanations, no placeholders, no TODOs.
