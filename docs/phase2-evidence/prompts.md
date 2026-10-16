# ELM Phase 2 Prompt Log

The following are the main implementation instructions used in the
development session. Tool responses and failed attempts are recorded in the
verification log; this file is not a verbatim export of the entire chat.

## Prompt 1 — Domain entities

Create modules/elm/domain/entities.py as an actual repository file.

- Define LeaveCategory with exactly CL, RH, SCL, EL, COL, and VL.
- Define frozen dataclasses LeaveRequestDateRange and LeaveRequest.
- Reject a date range where start_date is later than end_date.
- Use Python standard-library types and keep the domain independent of Django.
- Make an actual file edit rather than returning a plan.

## Prompt 2 — Domain exceptions

Create modules/elm/domain/errors.py.

Define ELMDomainError and specific exceptions:
InvalidDateRangeError, IneligibleCategoryError, InsufficientBalanceError,
OverlappingLeaveError, and InvalidWorkflowTransitionError.

Use Python standard-library features and create the actual repository file.

## Prompt 3 — Domain tests

Implement focused unit tests for the ELM domain foundation.

- Verify the six supported leave-category values.
- Test valid and reversed date ranges.
- Test LeaveRequest construction using the current API.
- Test inheritance and instantiation of the specific domain exceptions.
- Follow repository test conventions.
- Do not test business logic that has not yet been implemented.
- Do not modify unrelated modules.

## Prompt 4 — Test correction

After the generated test file contained duplicate classes and incorrect
imports, replace it with one clean unittest test module using imports from
modules.elm.domain.entities and modules.elm.domain.errors.

Preserve the existing production implementation and run the focused tests.

## Tool-use note

Aider generated some incorrect or duplicated content during initial attempts.
The test file was subsequently cleaned up manually. OpenCode was also tried,
but its session produced unrelated task content; it was not used as evidence
of a successful ELM implementation.

## Milestone: Continuous Leave-Day Counting

Implemented in `modules/elm/domain/policy.py`.

Function:
`count_continuous_leave_days(category, date_range)`

Behavior:
- Supports EL, COL, and VL only.
- Counts start and end dates inclusively.
- Includes weekends and closed holidays.
- Rejects CL, RH, and SCL for this continuous-counting operation.
- Rejects invalid argument types.

The implementation was written into the repository using PowerShell
after reviewing and correcting the proposed implementation. Aider's earlier
attempt contained incorrect weekday-only counting and duplicated domain
classes, so that proposal was not used as the final implementation.
