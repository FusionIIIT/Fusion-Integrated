# Gymkhana Module — State Machines

This document describes the state machine lifecycles implemented in the Gymkhana module.

---

## 1. Club Lifecycle

A Club represents a student society, sports council, or technical club.

```
       [ Client creates Club ]
                 │
                 ▼
          ┌──────────────┐
          │     OPEN     │ (Default initial state)
          └──────┬───────┘
                 │
                 │ approve_club (requires 'gymkhana.club.manage')
                 ▼
          ┌──────────────┐
          │  CONFIRMED   │ (Active club; sessions/events/memberships allowed)
          └──────────────┘
```

### Transition Specifications:
- **`OPEN` (initial)**: Created with valid coordinator, co-coordinator, and faculty councillor. Open clubs cannot host events, book venues, or accept membership applications.
- **`OPEN` $\to$ `CONFIRMED`**: Triggered by `approve_club(*, club_id: int)`. Requires `gymkhana.club.manage` permission (held by `Student Admin`). If called when status is already `CONFIRMED`, raises `ConflictError(code="club_not_open")`.

---

## 2. Membership Application Lifecycle

```
       [ Student applies ]
                 │
                 ▼
          ┌──────────────┐
          │     OPEN     │ (Pending review by club leadership)
          └──────┬───────┘
                 │
                 │ approve_membership (Club Head coordinator/co-coordinator)
                 ▼
          ┌──────────────┐
          │  CONFIRMED   │ (Official club member; eligible for member alerts)
          └──────────────┘
```

### Transition Specifications:
- **`OPEN` (initial)**: Created via `apply_for_membership(*, club, student_user_id, description)`. Requires the club to be in `CONFIRMED` status. Duplicate applications from the same student to the same club are rejected by DB unique constraint and `ConflictError(code="duplicate_membership")`.
- **`OPEN` $\to$ `CONFIRMED`**: Triggered by `approve_membership(*, application_id, club, actor_user_id, remarks)`. Authorized only for the current club coordinator or co-coordinator. Repeated approvals raise `ConflictError(code="membership_not_open")`.

---

## 3. Notification Outbox Lifecycle

The Gymkhana module implements the transactional outbox pattern for reliable asynchronous notification delivery.

```
       [ Service event enqueues outbox row ]
                         │
                         ▼
                  ┌──────────────┐
                  │   PENDING    │
                  └──────┬───────┘
                         │
                         │ claim_pending_batch
                         ▼
                  ┌──────────────┐
                  │   SENDING    │
                  └──────┬───────┘
                         │
           ┌─────────────┴─────────────┐
           │ Delivery succeeds          │ Delivery fails / raises OSError
           ▼                           ▼
    ┌──────────────┐            ┌──────────────┐
    │     SENT     │            │    FAILED    │ (attempts incremented,
    └──────────────┘            └──────────────┘  last_error logged)
```

### Transition Specifications:
- **`PENDING`**: Initial state inserted within the business service transaction. Deduplicated by `dedupe_key`.
- **`SENDING`**: Claimed with `select_for_update(skip_locked=True)`.
- **`SENT`**: Successfully dispatched via email service; records `sent_at`.
- **`FAILED`**: Network or OS socket error caught; records `last_error` and updates `attempts`.
