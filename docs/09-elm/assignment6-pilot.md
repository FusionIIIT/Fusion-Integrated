# Assignment 6: Employee Leave Management (ELM) pilot

This branch is a small integrated ELM implementation attempt against the current Fusion Base, **not** a complete production implementation of all 32 ELM coherent functional requirements. This is separate from the HR/EIS implementation on the `module/hreis` branch.

## Model and tool details

- Locally loaded model: **Qwen2.5-VL-7B** (`qwen/qwen2.5-vl-7b`)
- Parameters: **7B**, quantization **Q4_K_M** (4-bit GGUF)
- Local inference runtime: **LM Studio** OpenAI-compatible API on the student laptop
- Prompt/tool interaction: Python script calling the local API. Initial `models.py`, `domain/policy.py`, and `registry.py` responses were generated locally by Qwen. Those raw outputs and the API usage log were saved under `D:\HR(EIS)\lab6\evidence\elm_a6_raw_qwen25vl` and `elm_a6_local_qwen25vl_generation.jsonl` respectively.
- Integration: significant follow-up corrections and other files were created with additional GPT-6 assistance, **not** generated exclusively by Qwen. The original generated drafts contained incorrect leave calculations and an incompatible Fusion registry structure; these issues were corrected before submission.

This records the model actually exercised, rather than describing it as Qwen2.5-Coder (which was not the loaded local model for this branch). Existing earlier Lab 6 trials using other models are kept separately, untouched.

## Pilot workflows implemented

- Fusion IAM-backed module grants, roles, permission manifest, backend routing and client navigation, with no ELM login or user table
- Leave-category constants for CL, RH, SCL, EL, COL and VL; employee profiles with explicitly configured Unit Head / higher-sanction user IDs
- Admin-managed annual leave balances and individual published holiday entries
- Employee application with dates, purpose, optional Station Leave details, and CL half-day options
- Balance checking, date counting (continuous across weekends for EL/COL/VL), pending/approved overlap checking, and published-RH validation
- CL/RH final Unit Head decision; SCL/EL/COL Unit Head recommendation followed by higher sanction, with both recommendation outcomes continuing to final review
- Atomic final balance debit on approval; owner-only immediate withdrawal of pending applications; read-only employee history and leave-event records
- React pages for apply, own applications, balances, approvals and administration

## Intentional scope limits

This pilot does **not** fully implement the controlled ELM specification. The following remain future requirements and must not be described as completed:

- Faculty VL is deliberately blocked pending a reliable external Academic Calendar integration, rather than accepting unvalidated vacation dates.
- Approved-leave cancellation, extensions, resumption/attendance synchronization, substitute consent, year-end carry-forward/VL conversion, and Director self-sanction are not implemented.
- Automated institute entitlement allotment, full leave-policy configuration, medical-document handling, complete multi-authority establishment routing, durable scheduled SLA reminders/escalations and notification delivery are not connected.
- The holiday admin API maintains individual published dates rather than complete versioned calendar replacement.
- A clean IAM/PostgreSQL end-to-end demonstration has not been performed; the assignment clarification does not require exhaustive bug hunting or thorough testing.

The application rejects missing required profile/approval configuration and unsupported VL rather than fabricating institute policy. A separate HR administrator is required to configure example employee profile, balances and published restricted holiday entries before testing real request submission.

## Integration checks

Useful smoke checks:

```text
python manage.py check
python manage.py permission_manifest --check
python ops/checks/nav_matches_routes.py
python ops/checks/no_cross_module_fk.py
python -m pytest modules/elm/tests/test_policy.py
```

Database migration: `modules/elm/migrations/0001_initial.py`.

HTTP endpoints (mounted at `/api/v1/elm/`): `types`, `applications`, `applications/<id>/events`, `applications/<id>/withdraw`, `approvals`, `applications/<id>/decide`, `balances`, `admin/profiles`, `admin/balances`, `admin/holidays`. All protected endpoints require both the ELM module grant and the appropriate permission. Employee reads and writes derive the employee ID from the Fusion session.
