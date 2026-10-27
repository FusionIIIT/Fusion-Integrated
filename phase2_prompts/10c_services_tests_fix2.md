# Task: fix database marks and missing user_id in modules/leave/tests/test_services.py (output the COMPLETE file)

Fix the following issues in `modules/leave/tests/test_services.py`:

1. Add `pytestmark = pytest.mark.django_db` right after the imports at the top of the file.
2. In `application_instance` fixture: `LeaveApplication.objects.create` MUST include `user_id=1`.
3. In `director_app` fixture: `LeaveApplication.objects.create` MUST include `user_id=1`.
4. In `test_transition_cancellation_restores_balance`: `LeaveApplication.objects.create` MUST include `user_id=1`.
5. In `test_transition_substitute_accept_and_decline`: `LeaveApplication.objects.create` MUST include `user_id=1`.
6. In `test_actor_kind_recruiter`: fix function signature to `def test_actor_kind_recruiter():` (do not take `DummyPrincipal` as parameter).

Keep all other test logic and assertions completely intact.
Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
