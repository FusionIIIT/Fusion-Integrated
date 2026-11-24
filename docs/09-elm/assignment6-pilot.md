# Assignment 6: Employee Leave Management (ELM)

This module implements the Employee Leave Management (ELM) bounded context for Assignment 6 against `Fusion-Integrated`.

## Model and tool details

- Model: **Qwen2.5-Coder-7B** (`qwen2.5-coder:7b`, digest `dae161e27b0e`)
- Parameter size: **7B** (4.7 GB, quantization **Q4_K_M**)
- Inference runtime and coding agent: **Ollama** local runtime with **Aider v0.86.2** (`ollama_chat/qwen2.5-coder:7b`)

## Implemented capabilities

- **Platform & IAM integration**: Registered as `modules.elm` (`code: "leave_elm"`) with role grants (`Employee`, `Leave Approver`, `Leave Admin`), permission manifest, OpenAPI schema, and React routes under `/leave`.
- **Leave categories and eligibility**: Supports `CL`, `RH`, `SCL`, `EL`, `COL`, and `VL` (faculty-only eligibility for `VL`, published restricted holiday check for `RH`, published vacation window check for `VL`).
- **Day calculation and overlap rules**: Single-day `0.5` half-day support for `CL` on working days; continuous calendar-day counting across weekends and closed holidays for `EL`, `COL`, and `VL`; working-day counting for `CL`, `RH`, and `SCL`; non-overlap validation across active requests with the same-day different-half `CL` exception; `2:1` `VL`-to-`EL` conversion helper with accumulation cap.
- **Workflow and lifecycle**: Station Leave destination validation, optional substitute nomination and consent gate before Unit Head review, Unit Head final decision for `CL`/`RH`, Unit Head recommendation (`RECOMMENDED` / `NOT_RECOMMENDED`) followed by higher sanction authority decision for `SCL`/`EL`/`COL`/`VL`, atomic balance debit on final approval, immediate owner withdrawal of pending applications, pre-start cancellation of approved leave with balance restoration, and immutable `LeaveEvent` audit logging.

## Verification commands

```text
ruff check .
lint-imports
python ops/checks/no_cross_module_fk.py
python ops/checks/contracts_are_plural.py
python ops/checks/nav_matches_routes.py
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py permission_manifest --check
pytest modules/elm/tests/test_policy.py
```
