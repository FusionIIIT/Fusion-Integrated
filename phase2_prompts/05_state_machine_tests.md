# Task: write pytest tests for NEW module modules/leave/domain/state_machine.py (tests only, file modules/leave/tests/test_state_machine.py)

The transition table spec is in phase2_prompts/_state_table.md (read-only). Pattern for the module: modules/placement/domain/state_machine.py (read-only).
The module is pure Python. Tests are plain pytest, no database, no Django.
Import: `import pytest` and `from modules.leave.domain import state_machine as sm`.

## API under test
- constants named exactly as the state strings in uppercase: `sm.AWAITING_SUBSTITUTE == "awaiting_substitute"`, `sm.APPROVED`, `sm.WITHDRAWN`, ... (all 13 states).
- `sm.TERMINAL` frozenset = {rejected, withdrawn, cancelled}; `sm.PENDING` frozenset of the six pending new-leave states (awaiting_substitute, applicant_action_required,
  awaiting_unit_head, awaiting_establishment, awaiting_final_sanction, awaiting_director_self_sanction).
- `sm.UNIT_HEAD_FINAL == frozenset({"CL","RH"})`, `sm.HIGHER_SANCTION == frozenset({"SCL","EL","COL","VL"})`.
- exceptions: `sm.InvalidTransition`, `sm.ActorNotAllowed`, `sm.ScopeMismatch` (category class wrong for the transition).
- `sm.resolve(frm, to, actor_kind=None, category_code=None) -> Transition` (Transition has attributes frm, to, permission, actors, scope, guards).
  Raises InvalidTransition if no such edge; ActorNotAllowed if actor_kind given and not allowed; ScopeMismatch if category_code given and the edge scope is "unit_head_final"/"higher" and the code is not in that class.
- `sm.is_legal(frm, to) -> bool`; `sm.allowed_targets(frm, actor_kind=None) -> list[str]` (sorted).
- `sm.initial_state(substitute_required: bool, applicant_is_director: bool) -> str`.

## Tests required
1. initial_state: (True, False)->awaiting_substitute; (True, True)->awaiting_substitute; (False, True)->awaiting_director_self_sanction; (False, False)->awaiting_unit_head.
2. CL/RH happy path BW-EL-01: awaiting_unit_head -> approved and -> rejected by unit_head with category "CL" legal; same with "RH".
3. Unit-head approve for a higher-sanction category ("EL") raises ScopeMismatch; unit_head awaiting_unit_head -> awaiting_final_sanction with "EL" is fine and with "CL" raises ScopeMismatch.
4. Substitute loop BW-EL-03: awaiting_substitute -> applicant_action_required (substitute), -> awaiting_substitute (employee), -> awaiting_unit_head (substitute).
5. Director path: awaiting_substitute -> awaiting_director_self_sanction by substitute; awaiting_director_self_sanction -> approved/rejected by director; by unit_head raises ActorNotAllowed.
6. Higher-sanction route BW-EL-04: unit_head -> awaiting_establishment, establishment -> awaiting_final_sanction, authority -> approved / rejected.
7. Wrong actors: employee cannot approve (awaiting_unit_head -> approved, actor "employee" raises ActorNotAllowed); unit_head cannot move awaiting_final_sanction -> approved; employee cannot move awaiting_substitute -> awaiting_unit_head.
8. Withdrawal: for every state in sm.PENDING, resolve(state, "withdrawn", "employee") works and its permission is "leave_management.application.delete"; unit_head withdrawing raises ActorNotAllowed.
9. Illegal: withdrawn from approved, from cancellation_pending_unit_head, from each terminal state raises InvalidTransition; approved -> rejected raises InvalidTransition; awaiting_substitute -> awaiting_final_sanction raises InvalidTransition.
10. Terminal states have no outgoing edges: allowed_targets(s) == [] for s in TERMINAL.
11. Cancellation CW-EL-02: approved -> cancellation_pending_unit_head by employee; unit_head cancellation_pending_unit_head -> cancelled and -> approved (CL); with "VL" those two raise ScopeMismatch while -> cancellation_pending_final (VL) works;
    authority cancellation_pending_final -> cancelled and -> approved; cancellation_pending_establishment -> cancellation_pending_final by establishment.
12. Permission mapping: resolve(awaiting_unit_head, approved).permission == "leave_management.application.review"; resolve(approved, cancellation_pending_unit_head).permission == "leave_management.application.create";
    resolve(awaiting_substitute, awaiting_unit_head).permission == "leave_management.application.respond".
13. Table integrity: every Transition's frm and to are among the 13 states; no two Transitions share the same (frm, to); allowed_targets("awaiting_unit_head", "unit_head") == sorted(["approved","awaiting_establishment","awaiting_final_sanction","rejected"]).

Output the COMPLETE file only. No explanations, no placeholders, no TODOs. Blank lines must be completely empty. Max line length 100.
