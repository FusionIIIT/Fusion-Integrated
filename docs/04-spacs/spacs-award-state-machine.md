---
title: SPACS Convocation Award State Machine
module: spacs
status: approved
author: Sunkara Nandan (24BCS246)
reviewer: Pulkit Sharma (24BEC099)
last_reviewed: 2026-11-20
---

# Award State Machine Specification

## 1. Lifecycle States
- `nominated`: Candidate nominated by department, faculty, or automated academic criteria query.
- `shortlisted`: Filtered candidate meeting preliminary CPI and departmental clearance gates.
- `approved`: Formally approved by Director / Senate with recorded institutional reference.
- `published`: Publicly disseminated on portal and convocation bulletin.
- `revoked`: Post-approval sanction revoked due to disciplinary or academic breach.

## 2. Transition Diagram

```mermaid
stateDiagram-v2
    [*] --> nominated: nominate_candidate
    nominated --> shortlisted: shortlist_candidates
    shortlisted --> approved: record_senate_approval
    approved --> published: publish_awards
    approved --> revoked: revoke_award
    published --> revoked: revoke_award
    published --> [*]
    revoked --> [*]
```

## 3. Transition Guards
1. **Committee Quorum Guard**: Evaluation scores require minimum active committee member participation. Scores must strictly reside in [0, 100].
2. **Senate Clearance Guard**: Transition from `shortlisted` to `approved` requires a non-empty `approval_reference` matching Senate resolution conventions.
3. **Publication Lock**: Award outcomes cannot be modified once in `published` status.
