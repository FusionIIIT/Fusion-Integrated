# Task: fix a fixture error in modules/leave/tests/test_state_machine.py (output the COMPLETE file; keep every assertion)

pytest reports for 13 tests: `fixture 'sm' not found`. Cause: those test functions declare a parameter `sm`, e.g. `def test_cl_rh_happy_path(sm):`,
but `sm` is NOT a fixture. It is the module imported at the top of the file (`from modules.leave.domain import state_machine as sm`).
Fix: remove the `sm` parameter from EVERY test function signature (they become `def test_cl_rh_happy_path():`). Keep the module-level import
and keep all test bodies and assertions exactly as they are. Parametrized `test_initial_state` stays as is.
Blank lines must be completely empty. No explanations, no placeholders, no TODOs.
