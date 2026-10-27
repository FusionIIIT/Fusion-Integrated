# Task: fix fixtures in modules/leave/tests/test_selectors.py (output the COMPLETE file)

pytest failed because `LeaveApplication` and `LeaveBalance` require non-null database fields, and tests need database access.

1. Add `pytestmark = pytest.mark.django_db` at the top of the file.
2. Add imports:
   `from datetime import date`
   `from decimal import Decimal`
3. Add a category fixture:
   ```python
   @pytest.fixture
   def category():
       return LeaveCategory.objects.create(code="CL", name="Casual Leave")
   ```
4. Update application fixtures to supply `category`, `start_date`, `end_date`, `reason`:
   ```python
   @pytest.fixture
   def leave_application_1_own(category):
       return LeaveApplication.objects.create(
           user_id=1, category=category, start_date=date(2026, 1, 1),
           end_date=date(2026, 1, 2), reason="Personal", substitute_user_id=None
       )

   @pytest.fixture
   def leave_application_2_own(category):
       return LeaveApplication.objects.create(
           user_id=2, category=category, start_date=date(2026, 1, 3),
           end_date=date(2026, 1, 4), reason="Medical", substitute_user_id=None
       )

   @pytest.fixture
   def leave_application_1_substitute_3(category):
       return LeaveApplication.objects.create(
           user_id=1, category=category, start_date=date(2026, 1, 5),
           end_date=date(2026, 1, 6), reason="Conference", substitute_user_id=3
       )
   ```
5. Update balance fixtures to supply `category`, `year`, `balance_days`:
   ```python
   @pytest.fixture
   def leave_balance_1(category):
       return LeaveBalance.objects.create(
           user_id=1, category=category, year=2026, balance_days=Decimal("8.0")
       )

   @pytest.fixture
   def leave_balance_2(category):
       return LeaveBalance.objects.create(
           user_id=2, category=category, year=2026, balance_days=Decimal("8.0")
       )

   @pytest.fixture
   def leave_balance_3(category):
       return LeaveBalance.objects.create(
           user_id=3, category=category, year=2026, balance_days=Decimal("8.0")
       )
   ```
6. Keep all test functions and assertions intact.

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
