---
owner: security-owner
status: authoritative
last-reviewed: 2026-08-01
---

# Data Retention & Privacy

The system holds personal data for ~3,300 students and staff: identity, contact details, academic standing,
placement outcomes and salary figures. This document defines what is held, for how long, who may see it, and how
that is enforced.

---

## PII classification is structural

Classification is a **field type**, not a comment. `core/db/fields.py`:

```python
class PIIField(models.CharField):          """Personal but not sensitive: name, email, designation."""
class SensitivePIIField(models.CharField): """DOB, phone, address, category, gender, medical."""
class EncryptedField(models.BinaryField):  """Fernet at rest: TOTP secrets."""
```

Declaring a field with one of these types is what makes it protected, because three separate mechanisms read
the classification:

1. The **structlog redaction processor** — a `SensitivePIIField` value never reaches a log line.
2. The **export-audit check** — a serializer exposing one must be on a permission-gated, audited path.
3. The **retention job** — knows which columns to scrub on expiry.

A comment saying `# PII` does none of that. This is the mechanism that makes the rest of the document
enforceable rather than aspirational.

### Inventory

| Category | Fields | Class | Where |
|---|---|---|---|
| Identity | `username`, `display_name`, `email` | `PIIField` | `identity_user` |
| Credentials | `password_hash` | — (never exposed, never logged) | `identity_credential` |
| MFA secrets | `secret_enc` | `EncryptedField` | `identity_mfa_factor` |
| Session metadata | `ip`, `user_agent` | `SensitivePIIField` | `identity_session`, `identity_login_attempt` |
| Academic | `roll_no`, `cpi`, `earned_credits`, `active_backlogs`, `courses` | `PIIField` | `academics_*` |
| Demographic | `gender`, `category`, `date_of_birth` | **`SensitivePIIField`** | `directory_userref` |
| Contact | `phone`, `address` | **`SensitivePIIField`** | `directory_userref` |
| Placement | company, CTC, offer, record | `PIIField` (salary is personal) | `placement_*` |
| Documents | resumes, offer letters, certificates | file storage, UUID-keyed | `placement_document` |
| Company contacts | name, email, phone | `PIIField` / `SensitivePIIField` | `placement_companycontact` |

A student's **CTC is personal data**. It is treated as PII in exports and suppressed in aggregates — see
minimization below.

---

## Retention schedule

Enforced by beat tasks, not by policy documents.

| Data | Retention | Then | Task |
|---|---|---|---|
| `identity_login_attempt` | **90 days** | hard delete | `purge_login_attempts` |
| `identity_session` / `identity_refresh_token` | expiry + 7 days | hard delete | `purge_sessions` |
| `outbox_event` / `inbox_event` | 30 days after consumption | hard delete | `purge_events` |
| `audit_event` | **3 years** | **archive to cold storage — never deleted** | `archive_audit_events` |
| `placement_application` + transitions | **7 years** | anonymize (drop `user_id`, keep aggregates) | `anonymize_old_applications` |
| `placement_offer` / `placement_placementrecord` | 7 years | anonymize | same |
| `placement_document` | graduation + 2 years | delete the file, keep the metadata row | `purge_documents` |
| `academics_resultsnapshot` | graduation + 7 years | anonymize | `anonymize_old_snapshots` |
| `directory_userref` (archived users) | graduation + 7 years | scrub `SensitivePIIField`s, keep name and roll no | `scrub_archived_userrefs` |
| `placement_statssnapshot` | indefinite | — | aggregate, non-personal |
| journald logs | 30 days | rotate | systemd |
| Prometheus | 90 days | — | Prometheus |

### Why 7 years for placement data

Placement records back employment verification, alumni statistics, and NIRF/NAAC-style institutional
reporting. Seven years is the conventional Indian institutional retention period. **Anonymization rather than
deletion** preserves the historical aggregate — "the 2026-27 median CTC" must remain answerable in 2035 — while
removing the link to a person.

### Anonymization, not deletion

```python
def anonymize_application(app: Application) -> None:
    app.user_id = None                    # the link to a person is severed
    app.cover_note = ""
    app.resume = None
    app.anonymized_at = timezone.now()
    app.save(update_fields=["user_id", "cover_note", "resume", "anonymized_at"])
    app.transitions.update(actor_user_id=None)
```

Deleting rows would corrupt every historical statistic, which is worse for everyone including the individual.

**`audit_event` is never anonymized or deleted** — it is archived. An audit trail whose actor can be scrubbed is
not an audit trail. It is append-only at the database level (`UPDATE`/`DELETE` revoked for `iam_app`).

---

## Access control over PII

| Data | Who | Gate |
|---|---|---|
| Own record | the person | `*.view_self` |
| Student academic standing | acadadmin, dean, placement staff | `academics.standing.view`, scope-filtered |
| Student contact details | HR, placement staff | `PIIField` on a permission-gated serializer |
| `gender` / `category` | only where a programme genuinely requires it | **audited on every use**, including in an eligibility rule |
| Bulk student PII | placement/HR officers | `export.pii` — `is_dangerous`: MFA + step-up ≤5 min + audit with the filter and row count + 5/hour |
| Company contacts | placement staff | `company.view` |
| Aggregate statistics | public | suppressed where `placed < 5` |

**Every PII export writes an audit row containing the exact filter used and the row count returned** — not just
"an export happened". A year later, only the first form answers a real question.

Exports also carry a footer stamping the requester, timestamp and `request_id`, so a leaked spreadsheet is
traceable to a person.

---

## Minimization

Concrete, enforced choices:

- **No PII in JWT claims.** `sub` and `erp_uid` are opaque; there is no name, email or roll number. Asserted by
  test.
- **No PII in event payloads.** Events carry `user_id`; a consumer that needs a name calls
  `directory.contracts.get_users(ids)`. This keeps `outbox_event` — a 30-day queryable table — free of personal
  data.
- **Statistics suppress cells where `placed < 5`.** A single-placed-student cell plus a public median *is* that
  student's salary. Suppressed cells report the count and nothing else.
- **`gender` and `category` are available but audited.** Some employers run genuinely restricted drives; an
  unaudited category filter is a discrimination risk nobody would find later.
- **Request and response bodies are never logged.**
- **No third-party analytics** in the shell. No Google Analytics, no session recording, no external font CDN —
  which is also why the CSP can be strict with `connect-src 'self'`.

---

## Rights of the individual

| Right | How |
|---|---|
| Access | `/profile` shows their identity, standing and placement data. Documents downloadable. |
| Correction | Identity and contact via `profile.self.update`. **Academic data is corrected in the ERP** — we hold an immutable snapshot and cannot alter it ([academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md)). |
| Explanation of a decision | Eligibility shows per-rule outcomes ("CPI 6.80 — 7.00 required"); every offer-acceptance attempt persists its `policy_decision` with the actual numbers. |
| Export | `/profile/export` produces a JSON bundle of everything held about them. |
| Erasure | **Limited, and honestly stated below.** |

### Erasure — what we can and cannot do

On request, and subject to institutional approval:

- **Can:** scrub `SensitivePIIField`s (phone, address, DOB), delete uploaded documents, archive the account.
- **Cannot:** delete audit events (append-only, and required for integrity), delete academic snapshots within
  the retention window (institutional records), or delete a placement record within 7 years (employment
  verification and statutory reporting).

This is stated plainly rather than promised vaguely. A student asking for erasure gets an accurate answer about
what will and will not be removed.

---

## Access from outside the platform

| Route | Control |
|---|---|
| The legacy monolith | Owns the ERP. **We only read it, on a `SELECT`-only Postgres role.** |
| The sysadmin console | Its own permissions; absorbed in Phase 7 |
| Database access by an operator | Per-service least-privilege roles; audit and snapshot tables append-only; direct edits to `globals_*` detected by the reconciler |
| Backups | Off-box, encrypted at rest, restricted. **A restored backup contains full PII** — restore hosts are treated as production. |
| Development | Staging uses an **anonymized** ERP snapshot; local development uses factory data plus a small anonymized fixture. **A production dump is never copied to a laptop.** |

The last row is the one most often violated in practice. `make seed` exists so nobody has a reason to.

### The anonymization script

`ops/db/anonymize.sql`, run when producing a staging snapshot: replaces names with generated ones, emails with
`user<id>@example.invalid`, phone and address with fixed placeholders, scrambles DOB within the year, and
**preserves CPI, batch, discipline and placement outcomes** — because those are what make a staging environment
useful for testing eligibility rules.

---

## Verification

- Every `SensitivePIIField` value is redacted from logs — property test over nested structures.
- A test posts a password and greps the log output for it; must not appear.
- No log line contains a request body.
- JWT claims contain no PII.
- Event payloads contain no PII — a test walks every `fusion_contracts` model for PII-shaped field names.
- A PII export writes an audit row containing **both** the filter and the row count.
- A PII export without step-up returns 403 `step_up_required`.
- A statistics cell with `placed < 5` suppresses its CTC measures.
- Using `gender` or `category` in an eligibility rule writes an `audit_event`.
- Each retention task deletes or anonymizes exactly the intended rows on a fixture spanning the boundary date.
- Anonymized applications preserve aggregate counts — a stats snapshot before and after is unchanged.
- `UPDATE` and `DELETE` on `audit_event` raise `InsufficientPrivilege`.
- `anonymize.sql` leaves no recognizable name, email, phone or address, and preserves CPI and placement
  outcomes.
