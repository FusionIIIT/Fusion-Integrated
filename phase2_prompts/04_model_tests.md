# Task: write pytest tests for the leave models, file modules/leave/tests/test_models.py (tests only, complete file)

Models are in modules/leave/models.py (read-only context): LeaveCategory, LeaveApplication, LeaveApplicationTransition, LeaveBalance.
Use pytest-django: mark every test with `@pytest.mark.django_db`. Imports: `import pytest`, `from datetime import date`, `from decimal import Decimal`,
`from django.db import IntegrityError, transaction`, `from modules.leave.models import ...`.
For constraint violations use `with pytest.raises(IntegrityError), transaction.atomic():`.
Write a fixture `cl` that does `LeaveCategory.objects.create(code="CL", name="Casual Leave")` and a fixture `el` likewise for "EL"/"Earned Leave".
Write a helper `make_app(category, **overrides)` that creates a LeaveApplication with defaults user_id=1, start_date=date(2026, 11, 2), end_date=date(2026, 11, 2), reason="test".

Tests (exact intent):
1. test_same_user_can_apply_twice_for_same_category: create two applications for user 1 and category cl; count == 2 (the old unique constraint is gone).
2. test_default_status_is_awaiting_unit_head: make_app(cl).status == "awaiting_unit_head".
3. test_end_before_start_rejected: end_date=date(2026, 11, 1) with start_date=date(2026, 11, 2) raises IntegrityError.
4. test_half_day_on_single_day_allowed: half_day="first" with same start/end saves.
5. test_half_day_on_multi_day_rejected: half_day="first", end_date=date(2026, 11, 3) raises IntegrityError.
6. test_no_half_day_multi_day_allowed: half_day="" and a 3-day range saves.
7. test_extension_links_to_parent: parent = make_app(el); ext = make_app(el, kind="extension", parent=parent); ext.parent == parent and parent.extensions.count() == 1.
8. test_balance_unique_per_category_user_year: two LeaveBalance rows with the same category, user_id, year -> IntegrityError; a different year is fine.
9. test_balance_cannot_be_negative: balance_days=Decimal("-0.5") raises IntegrityError.
10. test_balance_keeps_fractions: balance_days=Decimal("2.50") round-trips from the database via refresh_from_db.
11. test_transition_records_audit_row: create a LeaveApplicationTransition(application=app, from_status="awaiting_unit_head", to_status="approved", actor_user_id=9, actor_label="unit_head"); app.transitions.count() == 1 and `at` is not None.
12. test_category_code_is_unique: duplicate code raises IntegrityError.
13. test_str_of_application_contains_status: "awaiting_unit_head" in str(make_app(cl)).

Output the COMPLETE file only. No explanations, no placeholders, no TODOs. Blank lines must be completely empty. Max line length 100.
