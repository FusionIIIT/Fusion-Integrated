# LMS State Machine

Companion: [domain model](lms-domain-model.md).

---

## Material lifecycle

```
Draft ──publish──► Published
  │
  └──schedule──► Scheduled ──release (beat)──► Published
```

| From | Event | To | Guard | BR |
|---|---|---|---|---|
| Draft | publish | Published | Faculty authorization | BR-005, BR-006 |
| Draft | schedule | Scheduled | Future release date set | BR-006 |
| Scheduled | release | Published | Release time reached | BR-006 |

## Assignment lifecycle

```
Draft ──publish (immediate)──► Available
  │
  └──publish (scheduled)──► Scheduled ──release (beat)──► Available
```

| From | Event | To | Guard | BR |
|---|---|---|---|---|
| Draft | publish_immediate | Available | All required fields valid | BR-009, BR-010, BR-011 |
| Draft | publish_scheduled | Scheduled | All required fields valid + future release | BR-009, BR-010, BR-011 |
| Scheduled | release | Available | Release time reached | BR-011 |

## Submission lifecycle

```
(none) ──submit──► Submitted ──grade──► Graded (Draft) ──release──► Released
```

| From | Event | To | Guard | BR |
|---|---|---|---|---|
| — | submit | Submitted | Type conformity + on-time (BR-012, BR-013) | BR-012, BR-013 |
| Submitted | grade | Graded (Draft) | Grading authority (BR-015) | BR-015, BR-016 |
| Graded (Draft) | release | Released | Faculty authority (BR-017) | BR-017, BR-018 |

## Grade lifecycle

```
Draft ──release──► Released ──change (instructor only)──► Released + GradeAudit
```

| From | Event | To | Guard | BR |
|---|---|---|---|---|
| Draft | release | Released | Faculty authority | BR-017 |
| Released | change | Released | Instructor only; audit logged | BR-019 |

## Illegal transitions

All illegal transitions are inexpressible — the declarative transition table in
`modules/lms/domain/state_machine.py` returns `None` for any `(state, event)` pair
not listed above. The service layer raises `ValueError` on `None`.