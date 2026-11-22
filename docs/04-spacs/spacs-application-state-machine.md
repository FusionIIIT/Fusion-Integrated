---
title: SPACS Scholarship Application State Machine
module: spacs
status: approved
author: Sunkara Nandan (24BCS246)
reviewer: Pulkit Sharma (24BEC099)
last_reviewed: 2026-11-20
---

# Application State Machine Specification

## 1. Lifecycle States
- `draft`: Applicant initiated; facts and evidence can be freely modified.
- `submitted`: Final submission by student; locked against direct edits.
- `under_scrutiny`: Assigned to SPACS Assistant for evidence verification.
- `correction_pending`: Returned to student for deficient document rectification.
- `verified`: Verification complete; all mandatory criteria verified by Assistant.
- `approved`: Terminal positive decision recorded by SPACS Convener.
- `rejected`: Terminal negative decision recorded by SPACS Convener.
- `withdrawn`: Applicant voluntarily withdrew prior to award approval.

## 2. Transition Diagram

```mermaid
stateDiagram-v2
    [*] --> draft: create_draft
    draft --> submitted: submit_application
    submitted --> under_scrutiny: assign_assistant
    under_scrutiny --> verified: mark_verified
    under_scrutiny --> correction_pending: request_correction
    correction_pending --> under_scrutiny: resubmit_correction
    verified --> approved: convener_approve
    verified --> rejected: convener_reject
    under_scrutiny --> rejected: convener_reject
    draft --> withdrawn: withdraw_application
    submitted --> withdrawn: withdraw_application
    under_scrutiny --> withdrawn: withdraw_application
    approved --> [*]
    rejected --> [*]
    withdrawn --> [*]
```

## 3. Transition Rules & Guards
1. **Uniqueness Guard**: Only one active (non-withdrawn, non-rejected) application permitted per student per scheme per academic cycle.
2. **Correction Iteration Guard**: Correction iterations bounded by policy threshold (maximum 2 rounds); exceeding threshold triggers automated escalation or rejection.
3. **Authorization Gate**: Only users with `spacs_convener` role may execute terminal transitions (`approved`, `rejected`). Assistants may only transition between `under_scrutiny`, `correction_pending`, and `verified`.
