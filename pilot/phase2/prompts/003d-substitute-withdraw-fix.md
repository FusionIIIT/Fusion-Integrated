Review of modules/leave/services/applications.py after task 003b found these defects. Fix only these, with SEARCH/REPLACE edits:

1. has_overlap builds leave_categories from the field choices and wraps policy.overlaps in `try: ... except Exception: continue`. Replace its body so that it filters LeaveApplication.objects.filter(user_id=user_id, kind=RequestKind.LEAVE, status__in=[Status.PENDING, Status.APPROVED]), applies exclude(id=exclude_id) when exclude_id is not None, and returns True as soon as policy.overlaps(app.start_date, app.end_date, app.half_day, start, end, half_day) is True; otherwise False. No try/except.

2. In replace_substitute, the loop over sub_apps wraps the overlap check in `try: ... except Exception: continue`, which swallows the LeaveError it raises, so a busy substitute is accepted. Replace the sub_apps query and the whole loop with:
    if has_overlap(substitute_id, app.start_date, app.end_date, app.half_day):
        raise LeaveError("The substitute is on leave on these dates.")

3. respond_to_substitute, replace_substitute and withdraw load the row with `LeaveApplication.objects.select_for_update().get(id=application_id)`, which raises DoesNotExist (HTTP 500) for an unknown id. In each of the three, use instead:
    app = LeaveApplication.objects.select_for_update().filter(id=application_id).first()
    if app is None:
        raise NotFound()

4. respond_to_substitute checks `app.status not in [Status.PENDING.value, Stage.SUBSTITUTE.value]`, which mixes a status with a stage, so a substitute can "respond" to a request that is already with the Unit Head. The condition must be: if app.status != Status.PENDING or app.stage != Stage.SUBSTITUTE: raise NotFound().

5. Remove the unused lines `from datetime import date as DateType` (they appear in has_overlap and apply_leave) and the unused variables old_status and new_status (in respond_to_substitute and withdraw).

Do not change anything else.
