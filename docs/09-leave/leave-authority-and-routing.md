---
owner: platform
status: reviewed
last-reviewed: 2026-10-12
---

# Leave authority and routing

Access combines an IAM module grant with an ELM permission and the task's employee/role scope.
The server scopes request and account querysets before serialization; hidden client links are not an
authorization control.

## Decision paths

- CL and RH: the applicant's Unit Head makes the final decision.
- SCL, EL, COL, and VL: the Unit Head recommends or does not recommend; the task continues through
  the current configured hierarchy to the final Sanctioning Authority.
- Establishment verification is included only when current route configuration requires it.
- The Director's own leave uses the Director self-sanction route.
- Cancellation follows the same route as the leave being cancelled. Extension uses the applicable
  Unit Head and higher-sanction path. Resumption goes to the original final Sanctioning Authority.
- Each task is assigned to a user from the employee/route projection. If an authority or Unit Head
  is missing, ELM stops submission with a configuration error rather than creating an unowned task.

## Permissions

| Permission family | Intended holder |
|---|---|
| Own request, balance, create, withdraw, cancellation | Employee roles |
| Substitute response | Current nominated substitute |
| Workflow task view and decision | Assigned Unit Head, Establishment role, or final authority |
| Policy, calendar, routing, SLA, and record maintenance | Leave Administrator |
| All-request/all-balance inspection | Explicit authorized operational roles |

Offline record maintenance and account corrections are separate from sanction permissions. An
administrator may record an already sanctioned paper request with reference evidence, but that
permission does not allow approving ordinary requests.

## Notifications and SLA

When an actionable task is assigned, ELM writes a deduplicated outbox message in the same transaction.
Final decisions notify the employee. Intermediate status changes remain available in request history.
Reminder and escalation thresholds are configured per role; scheduled processing rechecks that a
task is still pending before sending or changing its assigned responsibility. Every reminder and
escalation is recorded in the request audit history.
