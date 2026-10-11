---
owner: security-owner
status: authoritative
last-reviewed: 2026-08-01
method: STRIDE over the six highest-value flows
revisit: quarterly, and on any new external integration
---

# Threat Model

STRIDE applied to the six flows that matter: **login**, **token refresh**, **role assignment**, **apply to a
posting**, **accept an offer**, and **file download**.

Controls referenced by number are in [security-baseline.md](security-baseline.md).

---

## Assets, ranked

| Asset | Why it matters |
|---|---|
| Credentials and refresh tokens (~3,300 users) | Account takeover; some accounts hold `is_dangerous` permissions |
| The IAM signing key | **Total compromise** — an attacker mints valid tokens for any user, on every service |
| Declared academic results (CPI) | Determines who is eligible; altering it is exam fraud |
| Placement outcomes (offers, records) | Directly affects a student's career and salary |
| Student PII (roll no, DOB, phone, address, category, gender) | Statutory and reputational |
| Company contacts and CTC figures | Commercially sensitive; leakage damages employer relationships |
| The audit trail | Without it, none of the above is investigable |

---

## Trust boundaries

```
internet ──► nginx ──► [shell static | iam | platform | legacy | sysops]
                                 │            │
                       fusion_system_db   fusion_nonacad
                                 │            │
                                 └──► ERP (fusion_newui_prod) ◄── legacy owns it
                                       platform: SELECT only
                                       iam projector: 3 tables only
```

Every arrow crossing a box is a boundary. The three worth naming:

1. **browser → nginx** — everything untrusted.
2. **platform → ERP** — enforced by a Postgres grant, not by code (7.2).
3. **IAM signing key → every validator** — the highest-consequence single secret in the system.

---

## Flow 1 — Login

| S | Threat | Control |
|---|---|---|
| **S**poofing | Credential stuffing against reused passwords | Progressive lockout per username **and** IP (1.5) · throttle 5/min/IP + 10/h/username (§3) · optional HIBP check (1.4) · TOTP for privileged roles (1.8) |
| **S** | Username enumeration via error text or timing | Generic error (1.6) · constant-time dummy-hash comparison, verified statistically (1.7) |
| **T**ampering | Modified request in transit | TLS + HSTS preload (5.1, 5.2) |
| **R**epudiation | "I never logged in" | `identity_login_attempt` records username, IP, user-agent, outcome (90 d) |
| **I**nformation disclosure | **A traceback page leaking the auth cookie** | **P1 — `DEBUG=False` in legacy production. This is the blocking prerequisite.** |
| **I** | Password in a log | structlog redaction (6.2) · Sentry scrubber (6.3) |
| **D**oS | Login flood exhausting Argon2 CPU | Redis throttles shared across workers (§3) · `MemoryMax` (10.1) · Argon2 parameters chosen for ~100 ms, not maximal cost |
| **E**levation | Login returning more than it should | `/me` derives permissions server-side from the active role only (2.3) |

**Residual:** a phished password plus no MFA on a non-privileged account. Accepted — MFA is mandatory only for
`is_dangerous` roles. Mitigated by lockout and by session revocation on password change (1.12).

---

## Flow 2 — Token refresh

The highest-leverage flow, because a refresh token is a long-lived credential.

| S | Threat | Control |
|---|---|---|
| **S** | Stolen refresh token replayed | **Rotation with reuse detection** — a replay revokes the whole family (1.10) · `SameSite=Strict` + `Path=/…/auth` so it is never sent on ordinary API calls (5.8) |
| **S** | XSS reading the token | httpOnly cookies; **no token in JS** (5.8) · strict CSP with a nonce, no `unsafe-inline` (5.3) · `dangerouslySetInnerHTML` banned (4.8) |
| **T** | Forged JWT | RS256 — validators hold only the public key (1.15). HS256 would let a compromised legacy app mint tokens. |
| **T** | JWKS poisoning via a MitM'd fetch | Same-origin fetch through nginx; keys pinned by `kid`; two keys max |
| **R** | Disputed session activity | `identity_session` + `identity_refresh_token` chain via `parent` is a full lineage |
| **I** | PII in claims | **No PII in claims** (1.14) — asserted by test |
| **D** | Refresh flood | 60/hour per session (§3) |
| **D** | **Self-inflicted mass logout** — parallel 401s each firing a refresh, tripping reuse detection | **Single-flight refresh** on the client. This is a correctness requirement, not an optimization. Alert on `iam_refresh_reuse_detected_total` (10.5) — a spike means the client broke, not that we are under attack. |
| **E** | Stale role in a live token | 10-min access TTL bounds it. **To cut someone off now, revoke the session** (immediate, Redis denylist), not the role (1.13). |

**Residual:** the 10-minute permission-staleness window. A deliberate trade for local validation, so IAM being
down does not log everyone out ([ADR-0003](../01-architecture/adr/0003-rs256-jwt-access-plus-opaque-refresh.md)).

**Catastrophic case: signing-key compromise.** An attacker mints tokens for anyone, on every service including
the legacy monolith. Controls: `LoadCredential` (8.2), quarterly rotation (8.6), dual-`kid` so emergency
rotation is zero-downtime (1.16). Response: rotate, revoke all sessions, force re-login.

---

## Flow 3 — Role assignment

| S | Threat | Control |
|---|---|---|
| **E** | Self-granting a privileged role | `iam.role.assign` is `is_dangerous` — MFA + step-up ≤5 min (1.9) · audit on every use (2.8) |
| **E** | CSRF-driven grant from a malicious page | Double-submit CSRF, default-on (5.9) · `SameSite=Lax` (5.8) |
| **E** | Editing the ERP `globals_*` tables directly to grant a designation | From Phase 4 the reconciler **overwrites** hand edits and alerts on drift (10.5); the console's write endpoints return `410 Gone` |
| **T** | Role permissions changed without trace | `audit_event` with `before`/`after` (2.8); `UPDATE`/`DELETE` revoked on the audit table (7.5) |
| **R** | "I didn't grant that" | `rbac_user_role.granted_by` + `reason` + audit row |
| **I** | Enumerating roles or users | `iam.*.view` required; 404 for out-of-scope (2.5) |
| **D** | Projector flooding the ERP | Ordered per user, idempotent, pausable via `IAM_IS_ROLE_WRITER` |

**Residual (accepted, documented):** hazard **H1**. The legacy `unique_together ('working','designation')`
means only the `is_primary` holder projects, so a secondary holder's role is invisible in the legacy sidebar.
This is a **fidelity** gap, not a privilege escalation — the legacy app fails closed without the row. Tracked as
R-H1 in [risk-register.md](../08-delivery/risk-register.md).

---

## Flow 4 — Apply to a posting

| S | Threat | Control |
|---|---|---|
| **T** | **Applying while ineligible** | `is_eligible` is a server-side guard on the transition, re-evaluated if the cached evaluation is stale ([application-state-machine.md](../04-placement/application-state-machine.md)) |
| **T** | Eligibility rule changed after applications open, retroactively excluding someone | `eligibility_rule_locked_at` frozen on publish, backed by a **database `CheckConstraint`** so it holds even if the service is bypassed |
| **T** | Client-supplied CPI | CPI is **never** accepted from a client. It comes from `StudentAcademicStanding`, which comes from an immutable snapshot of the ERP's own computation ([ADR-0008](../01-architecture/adr/0008-declared-academic-snapshot-for-cpi.md)) |
| **T** | Grade tampering upstream to gain eligibility | Out of our trust boundary — the ERP owns grades. Detection: a nightly 2% snapshot re-pull asserting byte-equality alerts if a **declared** result's computation changes |
| **I** | Reading another student's application | Queryset filtered by ownership in the selector (2.4) · foreign id → **404** (2.5) |
| **I** | Enumerating applicants via sequential ids | 404 by construction; no id oracle |
| **R** | "I applied before the deadline" | `applied_at` + `ApplicationTransition` append-only + `cpi_at_apply` frozen |
| **D** | Apply-spam on deadline day | 30/hour per user (§3) · `Idempotency-Key` makes a double-click one application (4.13) |
| **D** | Posting-list page hammering the ERP | Eligibility **precomputed** on publish; the list is one indexed read over a partial index |

**Residual:** a student whose result is retracted after applying. Handled by design — a `ReviewFlag` for the
coordinator, **never an auto-rejection**, because a retraction may be a clerical correction and the student may
already have interviewed.

---

## Flow 5 — Accept an offer

The highest-value transaction in the system.

| S | Threat | Control |
|---|---|---|
| **T** | **Accepting two offers via two browser tabs** | `select_for_update` on `PlacementRegistration` (the per-student mutex) **plus** a partial unique index `PlacementRecord(user_id, placement_year) WHERE is_active` as a database backstop |
| **T** | Bypassing the policy through a bulk endpoint or a management command | Every path calls the same `services/offers.accept()`; the unique index holds even if it does not |
| **T** | Company re-tiered to retroactively legitimize an acceptance | `tier_rank` and `is_dream` are **copied at issue time**, never looked up later |
| **T** | Accepting after the deadline | `respond_by` checked in `can_accept`; `expire_offers` sweeps every 15 min |
| **T** | CTC edited post-publish to cross the dream threshold | Editing `ctc_lpa` is allowed (corrections are real) but **audited**, and the UI warns |
| **E** | Accepting someone else's offer | `offer.user_id != principal.erp_user_id` → 403 |
| **R** | "The system wouldn't let me accept" | **Every attempt, allowed or denied, persists its `Decision`** to `Offer.policy_decision` with the actual numbers |
| **I** | Seeing others' offers or CTCs | Selector-filtered; statistics suppress cells with `placed < 5` (6.5) |
| **D** | Revocation abuse | `offer.revoke` is `is_dangerous` — step-up + audit (1.9, 2.8) |

**Residual:** a coordinator with `offer.issue` can issue a favourable offer. Detection, not prevention:
`is_dangerous` audit plus the weekly privileged-access review (10.6). Separation of duties — coordinator drafts,
officer publishes and issues — is the structural control.

---

## Flow 6 — File download

| S | Threat | Control |
|---|---|---|
| **S** | Guessing another student's resume URL | UUID key **and** an authorization check on every fetch. **The token is a lookup key, not a bearer credential** (6.10) |
| **T** | Malicious upload served back (stored XSS, malware) | Extension ∩ magic bytes ∩ size ∩ sanitized name ∩ UUID key (4.1) · `Content-Disposition: attachment` + `nosniff` (4.2) · ClamAV **gating** download (4.3) · `pikepdf` strips PDF JavaScript (4.4) |
| **T** | Path traversal via filename | Filename never used as a path; storage key is a UUID (4.1) |
| **T** | XLSX/CSV formula injection executing on the recipient's machine | Cells starting `= + - @ \t \r` prefixed with `'` (4.10) |
| **I** | **Bulk PII exfiltration via export** | `export.pii` is `is_dangerous` — MFA + step-up (1.9) · 5/hour (§3) · audit records **the exact filter and row count** (6.4) · async with an expiring link |
| **I** | Zip bomb / decompression DoS | Size caps at nginx and in-app (4.5, 4.12); archives not expanded server-side |
| **D** | Large-file flood | 20 uploads/hour (§3) · nginx `client_max_body_size` (4.12) |

**Residual:** an authorized coordinator legitimately exporting PII and then mishandling the file. Not
technically preventable. Mitigated by the audit trail recording *which* PII, and by a footer stamping the
requester, timestamp and `request_id` into every export — so a leaked spreadsheet is traceable to a person.

---

## Cross-cutting

| Threat | Control |
|---|---|
| Insider with database access | Per-service least-privilege roles (§7) · snapshot and audit tables append-only (7.4, 7.5) · direct-edit drift detected by the reconciler |
| Compromised dependency | Lockfiles + `--frozen` · `pip-audit`, `pnpm audit`, CodeQL, Trivy (§9) · 7-day advisory triage |
| Compromised CI | Secrets not in CI variables; deploy is SSH + tag; `gitleaks` on every PR |
| Backup theft | Off-box, encrypted at rest, restricted access (10.4) |
| Log leakage | structlog redaction (6.2) · Sentry `send_default_pii=False` (6.3) · never log bodies or headers |
| Legacy monolith compromise | It holds only the JWT **public** key, so it cannot mint tokens (1.15). It does own the ERP, which is the real exposure — and the reason P1–P5 are blocking. |

---

## Accepted risks

| # | Risk | Why accepted | Compensating control |
|---|---|---|---|
| A1 | 10-min permission-staleness window | The price of local token validation, which keeps IAM off the academic system's critical path | Session revocation is immediate; `pv` makes staleness detectable |
| A2 | No MFA for ordinary students | Usability at ~3,000 users; they hold no dangerous permissions | Lockout, throttles, revocation on password change |
| A3 | Single VM — no HA | Cost and operational capacity | WAL archiving, off-box backups, a **tested** restore runbook |
| A4 | H1 projection gap | The legacy schema cannot represent multi-holder roles | Fails closed in legacy; allowlisted so drift alerts stay meaningful; the offices are told |
| A5 | Grade tampering upstream is out of scope | The ERP owns grades | Snapshot immutability + nightly byte-equality sampling detects post-declaration change |
| A6 | An authorized PII export can be mishandled | Not technically preventable | Filter + row count audited; exports stamped and traceable |

---

## Revisit triggers

Beyond the quarterly review: any new external integration · any new `is_dangerous` permission · any change to
token or cookie handling · any new file-upload surface · before the first full placement season (paired with a
penetration test) · after any security incident.
