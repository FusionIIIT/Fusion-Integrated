# Task: fix syntax error on line 8 in modules/leave/tests/test_services.py (output the COMPLETE file)

Line 8 currently has `@pytest.mark.django_db`, which is a decorator syntax error when placed before an import.
Change line 8 from:
`@pytest.mark.django_db`
to:
`pytestmark = pytest.mark.django_db`

Keep all other lines in the file exactly as they are. Output the COMPLETE file only.
Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
