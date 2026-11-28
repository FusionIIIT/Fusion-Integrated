# Gymkhana: model, lifecycles and operations

For the decisions behind this (rulings R1–R10 and H1–H9), read
[gymkhana-blueprint.md](gymkhana-blueprint.md). For where each spec id is enforced, read
[gymkhana-reference.md](gymkhana-reference.md).

## What the module holds

| Table | One row is | Notes |
|---|---|---|
| `gymkhana_club` | a club | `open` until Student Admin confirms it (BW-GYM-03) |
| `gymkhana_leadership_assignment` | one person in one seat for a period | the row with `valid_to` empty is current; a change ends it and starts a new one (BR-GYM-016) |
| `gymkhana_membership` | one student's application to one club | `open` then `confirmed`; one per student per club (BR-GYM-009) |
| `gymkhana_venue_list`, `gymkhana_venue` | a version of the venue list | the latest `effective_from` in the past is in effect; never edited (BR-GYM-020) |
| `gymkhana_venue_day` | a venue on a date | exists to be locked; every booking for that venue and date queues behind it (BR-GYM-006) |
| `gymkhana_booking` | a session or an event | both kinds share the table so overlap is one query |
| `gymkhana_poll`, `_poll_choice`, `_poll_target`, `_vote` | a poll, its choices, its audience, one vote | tallies are counted from votes, never stored (AFR-GYM-028) |
| `gymkhana_budget_request` | a club's budget request | always `open`; there is no approval in the baseline (AFR-GYM-031) |
| `gymkhana_event_report` | a club's event report | read only by the club's leaders and its councillor (BR-GYM-021) |
| `gymkhana_audit_event` | one write | ids and codes only; a vote's choice is never recorded there |
| `gymkhana_notification_outbox` | one notification | written with its cause, drained by a task |

People are integer IAM user ids. Nothing here references `fusionlab`; who is a student or
faculty member, and a student's batch and branch, come from `modules.directory`.

## Lifecycles

```
Club:        (none) --create, Student Admin--> open --approve, Student Admin--> confirmed
Membership:  (none) --apply, student--------> open --approve, Club Head-----> confirmed
```

`domain/state_machine.py` is the whole table. `confirmed` has no outgoing edge, and no
reject or cancel edge exists, so neither can be done by any path.

Who counts as a Club Head is decided by data, not by role: the current coordinator and
co-coordinator of a **confirmed** club (`selectors/scoping.py::led_clubs`). Every student
holds the Club Head permissions, and they reach only the clubs that student leads.

## Deployment order

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_gymkhana_venues --venue "<name>" [--venue "<name>" ...]
.venv/bin/python manage.py seed_modules
make permissions            # then, from Fusion_System_Administrator/Backend/backend:
./../venv/bin/python manage.py seed_iam_permissions --manifest <abs path>/registry/permissions.json
.venv/bin/python manage.py gymkhana_readiness
```

Until a venue list is seeded, `seed_modules` registers the module as `planned` and says
why, `gymkhana_readiness` exits non-zero with the same sentence, and booking answers 409
`no_venues_configured`. Everything else works.

To change the venues, seed a new list; the old one is kept:

```bash
.venv/bin/python manage.py seed_gymkhana_venues --venue "LHTC 101" --venue "OAT" \
  --effective-from 2027-01-01
```

The `Student Admin` designation does not exist in the ERP yet (open question H1). In
development, create and assign it from the IAM checkout:

```bash
./../venv/bin/python manage.py assign_role --user <account> --designation "Student Admin"
```

## Scheduled work

| Task | Beat | Queue | If it stops |
|---|---|---|---|
| `gymkhana.deliver_notifications` | every 60 s | `notifications` | no session, event or poll notification is sent; rows wait as `pending` and go out when it resumes |

A manual run: `.venv/bin/python manage.py gymkhana_deliver_notifications [--limit N]`.
It prints `expanded=… sent=… failed=… deferred=…`. A poll broadcast expands through the
IAM's academic directory; if the IAM is down the broadcast stays `pending` and is retried,
never sent to a partial audience.

## Known limitations of the baseline

- A booking cannot be cancelled (H7), so a mistaken booking holds its venue.
- A club's faculty councillor cannot be changed through the module; if the councillor
  leaves the faculty, events cannot be booked until it is changed by an operator.
- Inactive accounts cannot be told apart through `directory.get_users`, which carries no
  `is_active` field; validity is checked on kind (student or faculty) only.
