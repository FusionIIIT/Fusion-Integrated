# PMS State Machine (as implemented)

This describes `modules/pms/domain/state_machine.py`; the workflow specifications remain authoritative.

The main application lifecycle is stored in `PatentApplication.status`. Its legal edges are declared as `TRANSITIONS`, then checked by `validate_transition`. Budget and Attorney offer/response progress use their own PMS records; they do not become application statuses. Filing uses the derived `FilingWorkflowState.PRE_FILING_SATISFIED` only after the filing prerequisites are met.

## Main lifecycle paths

```text
Draft → Submitted → Under Review
                       ├─ Approved
                       ├─ Needs Revision → Resubmitted → Under Review
                       └─ Rejected → Resubmitted → Under Review
                                  └→ Appeal Submitted
                                      ├─ Rejection Upheld
                                      ├─ Remanded for Amendment → Resubmitted
                                      └─ Decision Modified

Approved → [separate budget/attorney substates and filing prerequisites]
         → Filed → Office Action Recorded
                   → Awaiting Applicant Approval → Applicant Approved
                   → Response Ready → Response Submitted
         → Granted → Renewal Decision Requested
                    ├─ Renewal Approved → Renewed
                    └─ Do Not Renew
```

Overdue revision paths may become `Expired`. The implementation records external grant outcomes rather than deciding grant. Appeal outcome `Decision Modified` has no downstream transition because the specification leaves that next state unresolved.

## Parallel and external workflows

Budget decisions and Attorney assignment offers are represented independently from application status, preserving the approved parallel pre-filing workflow. `AttorneyAssignment.status` records offer/accept/decline; budget decision state is in `PatentBudget`. Filing transitions are allowed only from the derived pre-filing-satisfied state, after the service checks prerequisites. Office-action, post-grant, maintenance, licensing, and legal-advice records retain their own process state.

This document is an implementation map only. It does not resolve the missing IAM-owned Director-domain projection or define the unspecified appeal outcome, budget authority, or external patent-office behavior.
