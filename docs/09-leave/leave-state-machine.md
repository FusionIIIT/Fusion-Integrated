---
owner: leave-lead
status: authoritative
last-reviewed: 2026-08-31
---

# Leave Request State Machine

A request's state changes **only** through `services/workflow.py::apply_event`, which resolves the move
against the table in `domain/state_machine.py` before writing anything. The table is declarative, so an
illegal transition is impossible to express rather than merely rejected.

Every row cites the workflow (`BW-EL-nn`) and the use case (`EL-UC-nnn`) it comes from. Two rows are
labelled **`(derived)`** — see [Gaps closed by analogy](#gaps-closed-by-analogy).

- **23 states**, 4 of them terminal: `CLOSED`, `REJECTED`, `WITHDRAWN`, `CANCELLED`.
- **24 events**, one of which (`OFFLINE_RECORD`) is deliberately not a transition.
- **46 transitions.**

`apply_event` takes a `select_for_update` on the request, refuses a terminal source, refuses the wrong
actor, writes a `RequestTransition`, and records any ledger movements — all in one transaction. A
balance can therefore never reflect a decision that was not recorded, and vice versa.

Several rows share a source and event and differ only in target, because the hierarchy decides where a
recommendation goes next. The caller supplies the target it resolved from the authority configuration;
`resolve()` refuses an ambiguous move rather than guessing.

---

## The table

| From | Event | To | Actor | Workflow | Use case |
|---|---|---|---|---|---|
| `DRAFT` | `SUBMIT` | `AWAITING_SUBSTITUTE` | Employee | BW-EL-01 | EL-UC-001 |
| `DRAFT` | `SUBMIT` | `AWAITING_UNIT_HEAD` | Employee | BW-EL-03 | EL-UC-001 |
| `DRAFT` | `SUBMIT` | `AWAITING_SELF_SANCTION` | Employee | BW-EL-03 | EL-UC-001 |
| `AWAITING_SUBSTITUTE` | `SUBSTITUTE_ACCEPT` | `AWAITING_UNIT_HEAD` | Substitute | BW-EL-01 | EL-UC-002 |
| `AWAITING_SUBSTITUTE` | `SUBSTITUTE_DECLINE` | `APPLICANT_ACTION_REQUIRED` | Substitute | BW-EL-02 | EL-UC-002 |
| `APPLICANT_ACTION_REQUIRED` | `RENOMINATE` | `AWAITING_SUBSTITUTE` | Employee | BW-EL-02 | EL-UC-006 |
| `APPLICANT_ACTION_REQUIRED` | `WITHDRAW` | `WITHDRAWN` | Employee | BW-EL-02 | EL-UC-007 |
| `AWAITING_UNIT_HEAD` | `UNIT_HEAD_APPROVE` | `APPROVED_NOT_STARTED` | Unit Head | BW-EL-03 | EL-UC-003 |
| `AWAITING_UNIT_HEAD` | `UNIT_HEAD_RECOMMEND` | `AWAITING_ESTABLISHMENT` | Unit Head | BW-EL-03 | EL-UC-003 |
| `AWAITING_UNIT_HEAD` | `UNIT_HEAD_RECOMMEND` | `AWAITING_FINAL_SANCTION` | Unit Head | BW-EL-03 | EL-UC-003 |
| `AWAITING_UNIT_HEAD` | `UNIT_HEAD_REJECT` | `REJECTED` | Unit Head | BW-EL-04 | EL-UC-003 |
| `AWAITING_ESTABLISHMENT` | `ROUTE` | `AWAITING_FINAL_SANCTION` | Establishment | BW-EL-03 | EL-UC-004 |
| `AWAITING_FINAL_SANCTION` | `SANCTION` | `APPROVED_NOT_STARTED` | Sanctioning Authority | BW-EL-03 | EL-UC-005 |
| `AWAITING_FINAL_SANCTION` | `REFUSE` | `REJECTED` | Sanctioning Authority | BW-EL-04 | EL-UC-005 |
| `AWAITING_SELF_SANCTION` | `SANCTION` | `APPROVED_NOT_STARTED` | Sanctioning Authority | BW-EL-03 | EL-UC-005 |
| `AWAITING_SELF_SANCTION` | `REFUSE` | `REJECTED` | Sanctioning Authority | BW-EL-04 | EL-UC-005 |
| `AWAITING_SUBSTITUTE` | `WITHDRAW` | `WITHDRAWN` | Employee | BW-EL-01 | EL-UC-007 |
| `AWAITING_UNIT_HEAD` | `WITHDRAW` | `WITHDRAWN` | Employee | BW-EL-03 | EL-UC-007 |
| `AWAITING_ESTABLISHMENT` | `WITHDRAW` | `WITHDRAWN` | Employee | BW-EL-03 | EL-UC-007 |
| `AWAITING_FINAL_SANCTION` | `WITHDRAW` | `WITHDRAWN` | Employee | BW-EL-03 | EL-UC-007 |
| `AWAITING_SELF_SANCTION` | `WITHDRAW` | `WITHDRAWN` | Employee | BW-EL-03 | EL-UC-007 |
| `APPROVED_NOT_STARTED` | `REQUEST_CANCELLATION` | `CANCELLATION_UNIT_HEAD` | Employee | BW-EL-05 | EL-UC-008 |
| `CANCELLATION_UNIT_HEAD` | `CANCELLATION_APPROVE` | `CANCELLED` | Unit Head | BW-EL-05 | EL-UC-008 |
| `CANCELLATION_UNIT_HEAD` | `CANCELLATION_ROUTE` | `CANCELLATION_ESTABLISHMENT` | Unit Head | BW-EL-05 | EL-UC-008 |
| `CANCELLATION_UNIT_HEAD` | `CANCELLATION_ROUTE` | `CANCELLATION_FINAL` | Unit Head | BW-EL-05 | EL-UC-008 |
| `CANCELLATION_UNIT_HEAD` | `CANCELLATION_REFUSE` | `APPROVED_NOT_STARTED` | Unit Head | BW-EL-06 | EL-UC-008 |
| `CANCELLATION_ESTABLISHMENT` | `CANCELLATION_ROUTE` | `CANCELLATION_FINAL` | Establishment | BW-EL-05 | EL-UC-004 |
| `CANCELLATION_FINAL` | `CANCELLATION_APPROVE` | `CANCELLED` | Sanctioning Authority | BW-EL-05 | EL-UC-005 |
| `CANCELLATION_FINAL` | `CANCELLATION_REFUSE` | `APPROVED_NOT_STARTED` | Sanctioning Authority | BW-EL-06 | EL-UC-005 |
| `APPROVED_NOT_STARTED` | `START` | `ONGOING` | Scheduler | BW-EL-09 | EL-UC-010 |
| `ONGOING` | `REQUEST_EXTENSION` | `EXTENSION_AWAITING_SUBSTITUTE` | Employee | BW-EL-07 | EL-UC-009 |
| `ONGOING` | `REQUEST_EXTENSION` | `EXTENSION_AWAITING_UNIT_HEAD` | Employee | BW-EL-07 | EL-UC-009 |
| `EXTENSION_AWAITING_SUBSTITUTE` | `SUBSTITUTE_ACCEPT` | `EXTENSION_AWAITING_UNIT_HEAD` | Substitute | BW-EL-07 | EL-UC-002 |
| `EXTENSION_AWAITING_SUBSTITUTE` | `SUBSTITUTE_DECLINE` | `EXTENSION_APPLICANT_ACTION_REQUIRED` | Substitute | BW-EL-07 | EL-UC-002 |
| `EXTENSION_APPLICANT_ACTION_REQUIRED` | `RENOMINATE` | `EXTENSION_AWAITING_SUBSTITUTE` | Employee | BW-EL-07 (derived) | EL-UC-006 |
| `EXTENSION_APPLICANT_ACTION_REQUIRED` | `WITHDRAW` | `ONGOING` | Employee | BW-EL-07 (derived) | EL-UC-007 |
| `EXTENSION_AWAITING_UNIT_HEAD` | `UNIT_HEAD_RECOMMEND` | `EXTENSION_AWAITING_ESTABLISHMENT` | Unit Head | BW-EL-07 | EL-UC-003 |
| `EXTENSION_AWAITING_UNIT_HEAD` | `UNIT_HEAD_RECOMMEND` | `EXTENSION_AWAITING_FINAL` | Unit Head | BW-EL-07 | EL-UC-003 |
| `EXTENSION_AWAITING_ESTABLISHMENT` | `ROUTE` | `EXTENSION_AWAITING_FINAL` | Establishment | BW-EL-07 | EL-UC-004 |
| `EXTENSION_AWAITING_FINAL` | `EXTENSION_GRANT` | `ONGOING` | Sanctioning Authority | BW-EL-07 | EL-UC-005 |
| `EXTENSION_AWAITING_FINAL` | `EXTENSION_REFUSE` | `ONGOING` | Sanctioning Authority | BW-EL-08 | EL-UC-005 |
| `ONGOING` | `REACH_END_DATE` | `AWAITING_RESUMPTION` | Scheduler | BW-EL-09 | EL-UC-010 |
| `ONGOING` | `SUBMIT_RESUMPTION` | `AWAITING_RESUMPTION_VERIFICATION` | Employee | BW-EL-10 | EL-UC-010 |
| `AWAITING_RESUMPTION` | `SUBMIT_RESUMPTION` | `AWAITING_RESUMPTION_VERIFICATION` | Employee | BW-EL-09 | EL-UC-010 |
| `AWAITING_RESUMPTION_VERIFICATION` | `RESUMPTION_QUERY` | `AWAITING_RESUMPTION_VERIFICATION` | Establishment | BW-EL-09 | EL-UC-011 |
| `AWAITING_RESUMPTION_VERIFICATION` | `VERIFY_RESUMPTION` | `CLOSED` | Establishment | BW-EL-09 | EL-UC-011 |
---

## Gaps closed by analogy

`BW-EL-07` row 4 enters `Extension Applicant Action Required` and the specification gives it no exit —
a request reaching it could never leave. The two missing rows were added by analogy with `BW-EL-02`,
`BW-EL-11` and `BW-EL-12`, which handle the identical situation for a *new* request whose substitute
declined: the applicant may nominate somebody else, or withdraw.

Both are labelled `BW-EL-07 (derived)` in the `workflow` column so they can be found and removed if the
specification is later revised to say something different. A test asserts there are **exactly two**
derived rows, so a third cannot be slipped in without a decision.

---

## `OFFLINE_RECORD` is not a transition

The workflow specification retires `WF-EL-06` on purpose: recording leave sanctioned on paper is
*single-actor record synchronisation, explicitly not a second approval*. So `record_offline` does not go
through `apply_event` — the request is born `CLOSED`, carrying its ledger movement and the name of
whoever entered it.

`OFFLINE_RECORD` exists in the `Event` enum only so the trail row can name what happened. It appears in
no transition, and `resolve()` refuses it from every state, which is the correct behaviour: `CLOSED` is
not reachable that way.

---

## Reading the trail

`GET /api/v1/leave/requests/<id>/trail` returns every transition in order, each with its actor, remark
and workflow citation. The client renders it as a timeline. Together with the ledger it answers the two
questions asked years later about any leave: what happened to it, and who decided.
