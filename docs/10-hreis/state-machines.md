# HR-EIS State Machines (Module 10)

This document specifies the exact states, valid transitions, guard conditions, and side effects for all life cycles in `modules/hreis`.

---

## 1. Leave Request Lifecycle

```
[Employee Applies]
        │
        ▼
   ( pending ) ──[Reject]──► ( rejected ) [Terminal]
        │
    [Forward]
        ▼
  ( forwarded ) ──[Reject]──► ( rejected ) [Terminal]
        │
    [Approve]
        ▼
   ( approved ) [Terminal: Deduct leave_balances in EmployeeServiceRecord]
```

### Transition Table

| Current State | Event / Action | Actor Guard | Next State | Side Effects |
|---|---|---|---|---|
| `*` (None) | `submit_leave` | Employee / Faculty | `pending` | Audit log `submit_leave_request`, in-app notification |
| `pending` | `forward` | Current Authority (`hod`) | `forwarded` | `current_authority_role` updated to next tier, audit log |
| `pending` | `reject` | Current Authority (`hod`) | `rejected` | Terminal state, rejection reason recorded, audit log |
| `pending` | `approve` | Final Authority (`director`) | `approved` | Terminal state, duration deducted from `leave_balances` |
| `forwarded` | `forward` | Intermediate Authority | `forwarded` | Next authority assigned, audit log |
| `forwarded` | `reject` | Current Authority | `rejected` | Terminal state, audit log |
| `forwarded` | `approve` | Competent Authority | `approved` | Terminal state, duration deducted from `leave_balances` |

---

## 2. LTC Claim Lifecycle

```
[Employee Applies]
        │
        ▼
   ( submitted )
        │
 [HR Admin Verify]
        ├─────────[Return]────► ( returned ) ──[Re-submit]──► ( submitted )
        ├─────────[Reject]────► ( rejected ) [Terminal]
        ▼ [Verified]
( pending_approval )
        │
    [Forward]
        ▼
  ( forwarded ) ──[Reject]────► ( rejected ) [Terminal]
        │
    [Approve]
        ▼
   ( approved ) ──[payment_status = processing]
        │
 [Accountant Settle]
        ▼
   ( settled ) [Terminal: payment_status = paid, passed_amount, voucher_no]
```

### Verification & Settlement Guards
- **HR Verification:** Only `hr_admin` role can verify (`verified`, `returned`, `rejected`).
- **Authority Approval:** Traverses configured hierarchy (`hod` -> `registrar` / `director`).
- **Settlement:** Only `accountant` can settle. Requires valid `passed_amount > 0` and non-empty `reference_id`.

---

## 3. CPDA Claim Lifecycle

```
[Faculty Submits]
        │
        ▼
   ( submitted )
        │
 [HR Admin Verify]
        ├─────────[Return]────► ( returned )
        ├─────────[Reject]────► ( rejected ) [Terminal]
        ▼ [Verified]
( pending_approval )
        │
    [Approve]
        ▼
   ( approved ) ──[disbursement_status = processing]
        │
 [Accountant Settle]
        ▼
   ( settled ) [Terminal: disbursement_status = paid, cpda_balance deducted]
```

### Invariants
- `passed_amount` cannot exceed remaining `cpda_balance` in `EmployeeServiceRecord`.
- Terminal state permanently deducts `passed_amount` from `cpda_balance` atomically (`select_for_update`).

---

## 4. Annual Faculty Appraisal Lifecycle

```
[HR Admin Opens Window]
        │
        ▼
[Faculty Submits] ──► ( submitted )
                           │
                 [HR Admin Assigns Reviewers]
                           ▼
                    ( under_review )
                           │
                [Reviewers Submit Evaluations]
                           ▼
                    ( under_review )
                           │
                [Director Finalizes]
                           ▼
                    ( finalized )
               [is_immutable = True]
        [Archived in EmployeeServiceRecord.service_history]
```

### Immutability & Window Rules
- Submission is rejected if `appraisal_window` is not active or `today > end_date`.
- Once `finalized`, the submission is permanently sealed (`is_immutable = True`). Any subsequent update, reviewer submission, or finalization raises `BadRequestError`.
