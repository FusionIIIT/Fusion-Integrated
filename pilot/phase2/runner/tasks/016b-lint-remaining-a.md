TITLE: Fix the ruff findings that need a human-style edit (views, policy, selectors, admin)
FORMAT: diff
EDIT: modules/leave/api/views.py modules/leave/domain/policy.py modules/leave/selectors.py modules/leave/services/admin.py
LIMIT: 900
POST: none
---
After ruff's automatic fixes, `ruff check .` still reports findings that ruff cannot fix safely. Fix only these, with SEARCH/REPLACE edits (do not change behaviour):

1. views.py, DecideView (SIM102, nested if): replace the nested establishment/sanction checks with two flat ifs:
        if app.stage == "establishment" and not request.principal.has_permission("leave.application.verify"):
            raise NotFoundError("You do not have permission to decide at this stage.")
        if app.stage == "sanction" and not request.principal.has_permission("leave.application.sanction"):
            raise NotFoundError("You do not have permission to decide at this stage.")
2. policy.py, entitlement() (RUF059): `carries_forward` is unpacked but never used; rename it to `_carries_forward` in that unpacking line.
3. policy.py (E501, lines over 100 characters, both inside docstrings): split the docstring line that ends "(no holiday calendar yet -> assume working days)." and the line "True when the date ranges intersect, except a single shared date where both halves are set and different." each onto two shorter lines.
4. policy.py, overlaps() (SIM102): replace the three nested ifs of the half-day exception with one:
    if a_start == b_start and a_half != "none" and b_half != "none" and a_half != b_half:
        return False  # different halves of the same day do not overlap (BR-EL-012)
5. selectors.py (E501): shorten the my_applications docstring to """Return a user's leave applications, newest first."""
6. selectors.py, visible_application (SIM102): replace the two nested ifs (owner/assignee, then substitute) with:
    if user_id not in (app.user_id, app.assignee_id, app.substitute_id):
        raise NotFoundError()
7. services/admin.py (RUF059): in set_reporting_line rename `created` to `_created` in `reporting_line, created = ReportingLine.objects.update_or_create(`.

Do not change anything else.
