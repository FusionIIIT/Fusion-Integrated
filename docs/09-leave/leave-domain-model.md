---
owner: platform
status: reviewed
last-reviewed: 2026-10-12
---

# Leave domain model

ELM owns leave facts and account history in its module database. It stores IAM user IDs as scalar
references and never joins another module's tables. See the [reference index](ELM_REFERENCE.md).

## Records

| Record | Purpose |
|---|---|
| `EmployeeProfile` | Current employee kind, designation, unit, Unit Head, and Director flag projected from HR/IAM. |
| `LeavePolicy` | One current parameter set for annual entitlements, COL evidence, and year-end boundary. |
| `LeaveCategory` | The fixed CL/RH/SCL/EL/COL/VL category catalogue. |
| `HolidayCalendar` | Draft, published, and superseded revisions of the institute holiday/RH calendar. |
| `VacationPeriod` | Read-only Academic Calendar vacation projection used to validate VL. |
| `LeaveRequest` | Draft, submitted, decision, cancellation, extension, resumption, and offline record. A follow-up links to its base request. |
| `WorkflowTask` | Ordered, queued or pending action assigned to a user and role. Only the active step is actionable. |
| `SubstituteResponse` | Append-only accept/decline records, including the single replacement traversal. |
| `LeaveSanction` | One decision or recommendation for a completed workflow task. |
| `LeaveAccountEntry` | Immutable credit/debit with a unique source key for retries and reconciliation. |
| `LeaveBalance` | Materialized per employee/category/year balance, updated only with a ledger entry. |
| `LeaveAuditEvent` | Append-only request lifecycle, SLA, and administrative action history. |
| `LeaveRouteConfiguration` | Current category and employee-context authority route, optional Establishment step, and substitute requirement. |
| `LeaveSLAConfiguration` | Current reminder/escalation threshold and escalation target for a workflow role. |
| `LeaveNotificationOutbox` | Transactional notification queue, retried independently of the business action. |

## Invariants

1. A request has its own generated ID; an employee can hold many requests.
2. Submission freezes the request fields. Later changes use a new cancellation, extension, or
   resumption request, except the explicitly allowed replacement of a declined substitute.
3. Every balance change has one `LeaveAccountEntry`. The unique source key makes approval,
   cancellation, offline recording, and year-end retries idempotent.
4. The cached `LeaveBalance` is an account summary; the ledger is the explanation for the balance.
5. Workflow tasks after the current action remain queued. Withdrawal cancels every outstanding task.
6. A negative Unit Head recommendation on a higher-sanction request continues to the configured
   final authority; it is not a rejection.
7. An approved leave record remains intact while its cancellation is considered. An approved
   cancellation reverses the original account debits.

## Ownership and synchronization

The HR/IAM integration supplies employee kind, designation, organizational unit, Unit Head, and
Director status. The Academic Calendar supplies vacation windows. ELM owns leave policy, holiday/RH
calendar revisions, request workflow, leave balances, and account history. No ELM operation writes
back to HR or the Academic Calendar directly; any attendance synchronization is an integration
contract to be supplied by the owning service.
