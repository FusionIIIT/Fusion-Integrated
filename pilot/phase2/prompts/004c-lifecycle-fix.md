Review of modules/leave/services/lifecycle.py from task 004b. Most of it is right; fix only these defects, with SEARCH/REPLACE edits:

1. Decimal is used in finalize() but never imported (ruff F821, NameError on approval). Add the line `from decimal import Decimal` directly below `from datetime import date`.

2. decide(), stage UNIT_HEAD, CL/RH (is_final True): after the approve/reject check nothing happens and the request stays pending forever (BR-EL-016). Directly after the line
                raise LeaveError(f"Unit Head must approve or reject for {category} leave.")
   and still inside `if is_final:`, add:
            log_action(app, actor_id, decision, remark)
            finalize(app, actor_id, decision == "approve")
            return app

3. decide(), stage UNIT_HEAD, other categories: it calls route_to_approver(app), which sends the request back to the Unit Head, so it never moves on (BR-EL-017/018). Replace the line `            route_to_approver(app)` (the one inside decide, after `app.unit_head_recommendation = decision`) with:
            if app.establishment_id:
                app.stage = Stage.ESTABLISHMENT
                app.assignee_id = app.establishment_id
            else:
                app.stage = Stage.SANCTION
                app.assignee_id = app.sanctioning_authority_id or app.user_id
            app.save()
            log_action(app, actor_id, decision, remark)

4. decide() and request_cancellation() load the row with `LeaveApplication.objects.select_for_update().get(id=application_id)`, which raises DoesNotExist (HTTP 500) for an unknown id. In both, use instead:
    app = LeaveApplication.objects.select_for_update().filter(id=application_id).first()
    if app is None:
        raise NotFound()

5. request_cancellation(): after the ownership check, the business-rule failures are not "not found"; they are bad requests. Change the four later `raise NotFound(...)` calls in request_cancellation (not LEAVE kind, not APPROVED, already started, pending cancellation exists) to `raise LeaveError(...)` with the same messages. Keep the ownership check as NotFound.

6. In finalize(), replace `raise ValueError("Cannot cancel a cancellation request.")` with `raise LeaveError("Cannot cancel a cancellation request.")`.

Do not change anything else.
