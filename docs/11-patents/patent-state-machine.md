# Patent Management System (PMS) — Lifecycle & State Machine

This document specifies the authoritative application state transitions, guards, business rules, and error handling for `modules.patents`.

---

## 1. Application Lifecycle States

The aggregate root `PatentApplication.status` transitions across 22 discrete states:

| State | Description | Category |
|---|---|---|
| `DRAFT` | Initial draft authored by applicant; unsubmitted | Pre-submission |
| `SUBMITTED` | Submitted for institutional review; awaiting Director assignment | Intake |
| `DIRECTOR_ASSIGNED` | Assigned to reviewing Director; conflict of interest cleared | Review |
| `UNDER_REVIEW` | Director technical evaluation in progress | Review |
| `NEEDS_REVISION` | Director requested technical revisions | Revision |
| `RESUBMITTED` | Revisions submitted by applicant | Review |
| `APPROVED` | Approved for patent filing; awaiting panel attorney assignment | Pre-filing |
| `REJECTED` | Rejected by Director; eligible for revision (60d) or appeal | Decision |
| `APPEAL_SUBMITTED` | Rejection formally appealed by applicant | Appeal |
| `APPEALED` | Appeal under evaluation by Director | Appeal |
| `DECISION_MODIFIED` | Appeal resolved with modified determination | Decision |
| `ATTORNEY_ASSIGNED` | Empanelled attorney assigned; awaiting acceptance | Drafting |
| `PENDING_REVIEW` | Attorney declined assignment; awaiting reassignment by Admin | Reassignment |
| `ASSESSMENT_IN_PROGRESS`| Attorney accepted; conducting patentability assessment | Assessment |
| `BUDGET_PENDING` | Filing budget drafted; awaiting financial approval | Budget |
| `FILED` | Officially filed with national or PCT patent office | Prosecution |
| `OFFICE_ACTION_PENDING` | Official examination report / objection received | Examination |
| `RESPONSE_SUBMITTED` | Response to examination report submitted | Examination |
| `GRANTED` | Formal patent rights awarded | Post-grant |
| `WITHDRAWN` | Withdrawn prior to external filing (BR-PMS-067..070) | Settled |
| `ABANDONED` | Prosecution ceased or maintenance lapsed | Settled |
| `EXPIRED` | Revision deadline exceeded without resubmission (BR-PMS-038) | Settled |

---

## 2. Transition Rules & Guards

```
[DRAFT] ──────────► [SUBMITTED] ──────────► [DIRECTOR_ASSIGNED] ──────────► [UNDER_REVIEW]
   │                      │                          │                            │
   │ (submit)             │ (assign_director)        │ (start_review)             │ (decision)
   │                      ▼                          ▼                            ▼
   │                 [WITHDRAWN]                [WITHDRAWN]            ┌──────────┴──────────┐
   │                                                                   │                     │
   ▼                                                                   ▼                     ▼
[WITHDRAWN]                                                       [APPROVED]            [REJECTED]
                                                                       │                     │
                                                                       │                     │ (appeal / revise)
                                                                       │                     ▼
                                                                       │            [APPEAL_SUBMITTED]
                                                                       │            [NEEDS_REVISION]
                                                                       │                     │
                                                                       ▼                     ▼
                                                              [ATTORNEY_ASSIGNED]      [EXPIRED]
                                                                       │
                                                       ┌───────────────┴───────────────┐
                                                       ▼                               ▼
                                              [PENDING_REVIEW]              [ASSESSMENT_IN_PROGRESS]
                                                       │                               │
                                                       └───────────────┬───────────────┘
                                                                       ▼
                                                                [BUDGET_PENDING]
                                                                       │
                                                                       ▼
                                                                    [FILED]
                                                                       │
                                                       ┌───────────────┴───────────────┐
                                                       ▼                               ▼
                                            [OFFICE_ACTION_PENDING]                [GRANTED]
                                                       │                               │
                                                       ▼                               ▼
                                             [RESPONSE_SUBMITTED]                 [ABANDONED]
```

### 2.1 Pre-Filing Withdrawal (`withdraw_application`)
* **Governing Rules**: `BR-PMS-067`, `BR-PMS-068`, `BR-PMS-069`, `BR-PMS-070`.
* **Guard**: Must provide a non-empty withdrawal justification reason. Application status must be member of `PatentPolicy.withdrawal_eligible_states`.
* **Result**: Transitions directly to `WITHDRAWN`. Once filed externally, PMS withdrawal is prohibited.

### 2.2 Director Assignment & Review Decision
* **Assignment Guard (`BR-PMS-022..027`)**: Reviewing director must not share inventorship conflict of interest (`director_user_id != applicant_user_id` and not in `co_inventors`).
* **Evaluation Guard (`BR-PMS-029..031`)**: Decision must be `APPROVE`, `REJECT`, or `REQUEST_REVISIONS`. Justification must be at least 50 characters long (`BR-PMS-031`).

### 2.3 Attorney Assignment, Acceptance & Decline
* **Assignment Guard (`BR-PMS-040..045`)**: Attorney must belong to empanelled roster, have active workload below capacity limit (default 5), and possess matching domain expertise.
* **Acceptance (`UC-PMS-011`)**: Transitions `ATTORNEY_ASSIGNED` $\to$ `ASSESSMENT_IN_PROGRESS`.
* **Decline (`BW-PMS-07`)**: Transitions `ATTORNEY_ASSIGNED` $\to$ `PENDING_REVIEW` for admin reassignment.

### 2.4 Resubmission & Revision Expiry
* **Resubmission (`BR-PMS-034`)**: Revision from `NEEDS_REVISION` or `REJECTED` must occur within `policy.revision_resubmission_days` (default: 60 days).
* **Expiry (`BR-PMS-038`)**: Celery sweep checks unrevised rejected/revision applications older than 60 days and transitions them to `EXPIRED`.

---

## 3. Subordinate Lifecycles

1. **Budget Ledger (`PatentBudgetLedger`)**:
   `REQUESTED` $\to$ `APPROVED` | `REJECTED` $\to$ `EXPENDED`.
2. **Office Actions (`OfficeActionRecord`)**:
   `PENDING` $\to$ `RESPONDED` $\to$ `CLOSED`.
