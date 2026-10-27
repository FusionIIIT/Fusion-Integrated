# Task: write modules/leave/domain/state_machine.py so every test in modules/leave/tests/test_state_machine.py passes

Read-only context: phase2_prompts/_state_table.md (the transition table, transcribe it row by row), the test file, and the pattern
modules/placement/domain/state_machine.py (copy its STRUCTURE: frozen dataclass Transition, TRANSITIONS tuple, `_INDEX` dict keyed by (frm, to), resolve/is_legal/allowed_targets).
Pure Python only (stdlib). NEVER import Django/DRF/Celery. Output the COMPLETE file.

Required content:
- module docstring (short, cite Workflow Specifications v1.6 CW-EL-01..03).
- 13 uppercase state constants: AWAITING_SUBSTITUTE = "awaiting_substitute", APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT,
  AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF_SANCTION, APPROVED, REJECTED, WITHDRAWN, CANCELLATION_PENDING_UNIT_HEAD,
  CANCELLATION_PENDING_ESTABLISHMENT, CANCELLATION_PENDING_FINAL, CANCELLED.
- TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED}); PENDING = frozenset of the six new-leave pending states.
- actor constants EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT, AUTHORITY, DIRECTOR, SYSTEM (strings "employee", "substitute", "unit_head", "establishment", "authority", "director", "system").
- UNIT_HEAD_FINAL = frozenset({"CL","RH"}); HIGHER_SANCTION = frozenset({"SCL","EL","COL","VL"}).
- permission constants P_CREATE, P_RESPOND, P_REVIEW, P_DELETE = the four full strings "leave_management.application.create|respond|review|delete".
- exceptions InvalidTransition(frm, to), ActorNotAllowed(actor_kind, frm, to), ScopeMismatch(category_code, scope) - each calls super().__init__ with a clear message.
- @dataclass(frozen=True) class Transition: frm, to, permission, actors: frozenset[str], scope: str = "any", guards: tuple[str, ...] = ().
- TRANSITIONS: tuple[Transition, ...] with EVERY row of the table (use a small helper for rows); the withdrawal rows generated with a generator expression over the six PENDING states.
- resolve(frm, to, actor_kind=None, category_code=None) -> Transition : look up `_INDEX[(frm, to)]` (InvalidTransition if missing); if actor_kind is not None and not in t.actors -> ActorNotAllowed;
  if category_code is not None: scope "unit_head_final" requires category_code in UNIT_HEAD_FINAL, scope "higher" requires category_code in HIGHER_SANCTION, otherwise raise ScopeMismatch.
- is_legal(frm, to) -> bool; allowed_targets(frm, actor_kind=None) -> sorted list of `to` values (optionally filtered by actor).
- initial_state(substitute_required: bool, applicant_is_director: bool) -> str per the table footnote.
Blank lines must be completely empty (no spaces). Max line length 100. No explanations, no placeholders, no TODOs.
