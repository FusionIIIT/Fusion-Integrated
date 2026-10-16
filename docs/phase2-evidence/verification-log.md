# ELM Phase 2 Verification Log

## Initial domain tests
Command:
python -m unittest modules.elm.tests.test_entities -v

Recorded result:
6 tests passed.

Covered:
- Exact leave-category values
- Valid date range
- Reversed date range rejection
- LeaveRequest construction
- Domain exception inheritance
- Domain exception instantiation

## Lint
A focused Flake8 command was run against the ELM domain and test files.

Recorded result:
Exit code 0 with no lint output for the selected checks.

## Diff check
Command:
git diff --cached --check

Recorded result:
No whitespace errors were reported. Git previously warned that LF line
endings may be converted to CRLF on Windows; this was a line-ending warning.

## Test environment note
The command pytest modules/elm/tests/ could not run because pytest was not
available as a recognized PowerShell command. The tests were run successfully
using Python's built-in unittest runner instead.

## Current limitations
These results verify only the initial domain foundation. They do not verify
entitlements, CL half-day calculations, RH calendar rules, eligibility,
overlap detection, approval workflows, database persistence, API behavior,
permissions, or frontend integration.

Update this file with new commands and their actual outcomes after every
subsequent implementation milestone.

## Continuous leave-day counting milestone

Command:
`python -m unittest modules.elm.tests.test_entities -v`

Actual result:
12 tests passed in 0.003 seconds.

Additional verification:
- Focused Flake8 command completed with exit code 0.
- `git diff --check` reported no whitespace errors.
- Git emitted a Windows LF/CRLF line-ending warning for the test file.
  This is a warning, not a test failure.

Additional test coverage:
- EL, COL, and VL count inclusive calendar days.
- A one-day interval counts as one day.
- Friday through Monday counts as four calendar days.
- CL, RH, and SCL are rejected by this function.
- Incorrect argument types are rejected.
- `datetime` boundaries are rejected by the date-only policy.

Limitations:
This function calculates continuous calendar days only. It does not yet
implement leave balances, entitlement enforcement, employee eligibility,
RH calendar validation, overlap detection, or approval workflows.

## Milestone: Sufficient-Balance Validation

Implemented in `modules/elm/domain/policy.py`.

Function:
`validate_sufficient_balance(available_balance, requested_days)`

Verified behavior:
- Accepts non-negative integer and Decimal quantities.
- Supports fractional leave values such as 0.5.
- Rejects negative values and invalid argument types.
- Rejects non-finite Decimal values.
- Raises InsufficientBalanceError when the requested amount exceeds
  the available balance.

Verification command:
`python -m unittest modules.elm.tests.test_entities modules.elm.tests.test_policy -v`

Recorded result:
19 tests passed.

Focused Flake8 checks completed with exit code 0.

Limitations:
This validates a supplied balance and requested quantity. It does not
calculate annual entitlement, determine employee eligibility, or deduct
leave from a database balance.

## Annual leave limits — 2026-10-17

- Added annual-limit policy handling for CL, RH, SCL, EL, VL, and COL.
- EL is limited to 30 days for non-faculty employees; the faculty EL limit remains unspecified.
- VL is limited to eligible faculty, with a limit of 60 days.
- COL requires explicit eligibility; the configured limit is 20 days.
- SCL's 15-day value represents a maximum, not an automatic grant.
- Verification: 26 unit tests passed across the entity, balance-policy, and entitlement-policy test modules.
- Focused Flake8 check for selected syntax and undefined-name errors returned exit code 0.
- Scope limitation: these results verify the tested domain helpers, not the complete ELM application or its approval workflows.
