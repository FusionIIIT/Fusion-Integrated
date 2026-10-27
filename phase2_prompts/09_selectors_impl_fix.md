# Task: fix permission-first check in modules/leave/selectors/applications.py (output the COMPLETE file)

In `modules/leave/selectors/applications.py`, check permissions BEFORE checking `actor.user_id`.
Administrators / reviewers who hold the view permission see all applications or balances regardless of whether `actor.user_id` is set.
Only callers without the view-all permission fall back to filtering by `actor.user_id`.

Required logic:
```python
def applications_for(actor):
    """Returns applications visible to the actor."""
    base = LeaveApplication.objects.select_related("category")
    if getattr(actor, "has_permission", lambda p: False)("leave_management.application.view"):
        return base

    user_id = getattr(actor, "user_id", None)
    if not user_id:
        return LeaveApplication.objects.none()

    return base.filter(
        models.Q(user_id=user_id) | models.Q(substitute_user_id=user_id)
    )


def balances_for(actor):
    """Returns balances visible to the actor."""
    base = LeaveBalance.objects.select_related("category")
    has_perm = getattr(actor, "has_permission", lambda p: False)
    if has_perm("leave_management.balance.view") or has_perm("leave_management.balance.manage"):
        return base

    user_id = getattr(actor, "user_id", None)
    if not user_id:
        return LeaveBalance.objects.none()

    return base.filter(user_id=user_id)
```

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
