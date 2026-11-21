# IAA — Spec Notes (grounded reference, v1.3 FINAL specs)

Condensed from the real spec package (`02` Requirement Registry, `03` Use Case
Specs, `04` Business Rule Specs, `05` Workflow Specs). Keep this file next to
the code; it's the thing the generated backend is actually derived from.

## What this backend slice covers

Implemented: the core Expense/Voucher, TA Claim, Anomaly, and Audit
Observation lifecycles (services.py / domain.py / models.py / api/).

Not implemented (out of scope for this <1000-line backend slice —
reporting/admin, not core workflow):
- UC-304 Create Automatic Anomaly (system-raised anomalies)
- UC-504 Review Financial Records for Audit
- UC-601..604 Reports, dashboards, exports, notifications
- UC-701..704 Role switching/assignment and hierarchy/policy configuration

## Business Rules (all 19, IAA-BR-xxx)

| ID | Statement |
|----|-----------|
| BR-001 | A creator/claimant must not approve the same expense/voucher request or TA claim. |
| BR-002 | Required approval levels and assignees are determined by configured amount, request type, department, and hierarchy rules. |
| BR-003 | A user holding multiple IAA roles must explicitly activate the role under which a role-specific action is performed. |
| BR-004 | System Admin configuration privileges do not grant access to operational financial request content or approval actions. |
| BR-005 | Every approval or rejection decision must record remarks together with decision identity and timestamp. |
| BR-006 | Process/Record actions and Recorded terminal states represent internal governance/record completion only — must not execute or imply a bank/payment transfer. |
| BR-101 | Mandatory fields/documents are required for formal submission, but not for saving an incomplete Draft. |
| BR-102 | Applicable requests/claims must be compared with available departmental budget during Finance validation. |
| BR-103 | Material policy/budget/financial anomalies are recorded and tracked; ordinary completeness errors are not automatically anomalies. |
| BR-104 | A formally submitted request/claim is read-only to its creator for ordinary edits; only structured response/correction actions are permitted. |
| BR-201 | A submitted TA claim must satisfy configured TA policy/documentary requirements before it may be treated as verified. |
| BR-202 | TA claims meeting configured high-value criteria require authority approval under the configured approval route. |
| BR-301 | Audit observations use only Open, Responded, Closed states; audit history must not be deleted. |
| BR-302 | An observation may be closed only after the Auditor verifies the response, corrective action, and supporting evidence. |
| BR-401 | A pending authority approval exceeding the configured time limit auto-escalates to the next eligible configured authority. |
| BR-501 | A user may invoke IAA functions / view IAA data only within the active role's permissions and record ownership/assignment scope. |
| BR-502 | Changing a role assignment does not alter historical actions or the identity/role recorded on completed actions. |
| BR-503 | Relevant IAA actions must be logged with user identity, active role, timestamp, action, and resulting status. |
| BR-504 | Notifications are generated for submission/status changes, approval/rejection/escalation, anomaly/audit-observation events, and overdue actions. |

Where each rule is enforced in code:
- BR-001 → `domain.check_segregation_of_duties` (used in `decide_expense`, `decide_ta_claim`)
- BR-002 → `domain.more_approval_levels_required` (`approval_level` vs `approval_levels_required`)
- BR-005 → `domain.require_remarks`
- BR-006 → `process_record_expense`/`process_record_ta_claim` only flip status, never touch payment
- BR-101 → `domain.check_submission_completeness` (draft vs formal submit)
- BR-102 → `domain.check_budget_available`, called from `finance_review_expense`/`verify_ta_claim`
- BR-103 → budget shortfalls create an `Anomaly` row rather than a generic validation error
- BR-202 → `domain.is_high_value` sets `TAClaim.is_high_value`, used to route to `APPROVAL_PENDING` instead of `VERIFIED`
- BR-301 → `AnomalyStatus`/`ObservationStatus` TextChoices restrict the state set
- BR-302 → `domain.can_close_observation`
- BR-401 → `escalate_overdue_expense` (caller supplies the next authority; no scheduler in this slice)
- BR-503 → `services._log()` writes an `AuditLogEntry` on every service call

BR-003, BR-004, BR-501, BR-502, BR-504 are role/permission/notification concerns
handled by the platform's auth layer (`registry.py` PERMISSIONS/ROLE_GRANTS,
`fusion_auth.permissions.HasPermission`) and the (not-yet-built) notifications
piece — not re-implemented inside this module.

## Use Cases (27 total, IAA-UC-xxx)

**Expense/Voucher (implemented):**
UC-101 Create Draft · UC-102 Submit · UC-103 Finance Review/Validate ·
UC-104 Respond to Finance Query · UC-105 Process & Record Approved Request ·
UC-201 Approve/Reject · UC-202 Handle Escalated Approval · UC-203 Escalate Overdue

**Anomalies (implemented):**
UC-302 Flag Anomaly · UC-303 Resolve or Escalate Anomaly
(UC-304 Create Automatic Anomaly — not implemented, see scope note above)

**TA Claims (implemented):**
UC-401 Submit TA Form · UC-402 Verify TA Form ·
UC-403 Approve/Reject High-Value TA · UC-404 Process & Record TA

**Audit (implemented):**
UC-501 Raise Observation · UC-502 Respond to Observation ·
UC-503 Review & Close Observation
(UC-504 Review Financial Records for Audit — not implemented)

**Reporting/Admin (not implemented, out of scope):**
UC-601 View Reports & Dashboards · UC-602 Export Report ·
UC-603 Track Own Request/TA Status · UC-604 View Notifications ·
UC-701 Switch Active Role · UC-702 Manage Role Assignments ·
UC-703 Configure Approval Hierarchy & Thresholds ·
UC-704 Configure Financial Year & Policy Parameters

## State lifecycles (`models.py`)

- `RequestStatus` (Expense/Voucher): DRAFT → SUBMITTED → QUERY_RAISED (→ SUBMITTED) /
  FINANCE_VALIDATED → APPROVAL_PENDING → (ESCALATED ↔ APPROVAL_PENDING) → APPROVED/REJECTED → RECORDED
- `TaStatus` (TA Claim): SUBMITTED → QUERY_RAISED (→ SUBMITTED) / VERIFIED or
  APPROVAL_PENDING (if high-value) → (ESCALATED) → APPROVED/REJECTED → RECORDED
- `AnomalyStatus`: OPEN → RESOLVED or ESCALATED
- `ObservationStatus`: OPEN → RESPONDED → CLOSED (or back to OPEN if unsatisfactory, BR-302)

## Workflow pattern (worked example: BW-IAA-01)

`BW-IAA-01 — Expense/Voucher Standard Success` is the basis workflow;
`BW-IAA-02..06` are its traversal/rejection/escalation variants, all sharing
`CW-IAA-01` (the common sub-workflow for Expense/Voucher). The same
basis+variant+common-subworkflow pattern repeats per area:

| Area | Basis workflows | Common sub-workflow |
|------|-----------------|----------------------|
| Expense/Voucher | BW-IAA-01..06 | CW-IAA-01 |
| TA Claims | BW-IAA-07..11, 16, 17 | CW-IAA-02 |
| Anomalies | BW-IAA-12, 13, 18, 19 | CW-IAA-03 |
| Audit Observations | BW-IAA-14, 15 | CW-IAA-04 |

Concretely, for the expense path: `create_draft_expense` (UC-101) →
`submit_expense` (UC-102) → `finance_review_expense` (UC-103 — either
`FINANCE_VALIDATED`, a `QUERY_RAISED` loop back through `respond_query_expense`
(UC-104), or a budget `Anomaly`) → `decide_expense` one or more times per
`approval_levels_required` (UC-201, looping to `APPROVAL_PENDING` until the
last level, or short-circuiting to `REJECTED`) → optionally
`escalate_overdue_expense` (UC-203/202) → `process_record_expense` (UC-105,
only from `APPROVED`, per BR-006 never touching payment). TA claims and
anomaly/audit flows follow the equivalent shape in `services.py`.
