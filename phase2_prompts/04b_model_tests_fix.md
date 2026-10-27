# Task: fix ONE test in modules/leave/tests/test_models.py (output the COMPLETE file, every other test unchanged)

`test_category_code_is_unique` fails with:
  django.db.utils.IntegrityError: duplicate key value violates unique constraint "leave_category_code_key"  Key (code)=(CL) already exists.
Cause: the fixture `cl` already created code "CL", and the test creates "CL" AGAIN outside `pytest.raises`. Rewrite the test body to exactly:

@pytest.mark.django_db
def test_category_code_is_unique(cl):
    """LeaveCategory.code is unique."""
    with pytest.raises(IntegrityError), transaction.atomic():
        LeaveCategory.objects.create(code="CL", name="Duplicate")

Also: blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
