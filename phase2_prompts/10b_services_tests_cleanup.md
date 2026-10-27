# Task: fix and clean up modules/leave/tests/test_services.py (output the COMPLETE file)

Fix the following issues in `modules/leave/tests/test_services.py`:

1. State constants import:
   Import `APPLICANT_ACTION_REQUIRED` instead of `PENDING` from `modules.leave.domain.state_machine`.
   (The 13 state constants are: AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF_SANCTION, APPROVED, REJECTED, WITHDRAWN, CANCELLATION_PENDING_UNIT_HEAD, CANCELLATION_PENDING_ESTABLISHMENT, CANCELLATION_PENDING_FINAL, CANCELLED).

2. Fix `actor_kind` tests (Leave uses domain actors: employee, substitute, unit_head, establishment, authority, director, system; NEVER student, staff, or recruiter):
   - `assert leave_services.actor_kind(None) == "system"`
   - `assert leave_services.actor_kind(user_principal, application_instance) == "employee"`
   - When principal has user_id=99 and application has substitute_user_id=99 (and status is awaiting_substitute):
     `assert leave_services.actor_kind(sub_principal, app) == "substitute"`
   - When principal has permission "leave_management.application.review" and app is in awaiting_unit_head:
     `assert leave_services.actor_kind(uh_principal, application_instance) == "unit_head"`
   - When applicant_is_director is True and user is applicant and status is awaiting_director_self_sanction:
     `assert leave_services.actor_kind(user_principal, director_app) == "director"`

3. In `test_apply_cl_happy_path`:
   The initial transition recorded on application creation has `from_status == ""` (empty string), NOT "draft".
   Change: `assert transitions.first().from_status == ""`

4. In `test_transition_substitute_accept_and_decline`:
   When substitute declines, the target status is `APPLICANT_ACTION_REQUIRED`:
   `to_status=APPLICANT_ACTION_REQUIRED`
   `assert app.status == APPLICANT_ACTION_REQUIRED`

5. Ensure `pytestmark = pytest.mark.django_db` is defined at the top of the file.

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
