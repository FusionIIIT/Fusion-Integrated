---
owner: iam-lead
status: authoritative
last-reviewed: 2026-08-01
audience: whoever is running the cutover, at the time they are running it
---

# Auth Migration Runbook

Moving ~3,277 live users onto central authentication, without an outage and without a forced password
reset. This is the highest-risk sequence in the programme.

**The property that makes it safe:** existing DRF tokens keep working at every step. A rollback never
requires anyone to log in again.

**Every step is behind a flag that defaults to off.** No step is entered until the previous one's gate has
held.

---

## Flags

| Flag | Where | Default | Effect | Rollback |
|---|---|---|---|---|
| `IAM_JWT_AUTH_ENABLED` | legacy env | off | legacy accepts IAM cookies | unset + `systemctl restart fusion` (~30 s) |
| `IAM_JWT_AUTH_ENABLED` | sysadmin env | off | console accepts IAM cookies | unset + restart |
| `IAM_LOGIN_ENABLED` | shell env | off | `/app/login` uses IAM | route `/app/login` → legacy login |
| `IAM_IS_ROLE_WRITER` | iam env | off | projector writes the `globals_*` tables | unset — projector pauses, events queue, nothing lost |
| `IAM_MINT_LEGACY_TOKEN` | iam env | **on** | IAM also creates an `authtoken_token` row at login | leave on; it is the safety net |
| `LEGACY_LOGIN_ENABLED` | legacy env | **on** | `/api/auth/login/` still works | do not turn off before Phase 4 + 30 days |

---

## Phase 0 — Prerequisites (blocking)

Nothing below starts until all of these are true.

```bash
cd /path/to/Fusion/FusionIIIT

# 1. Production settings hardened — DEBUG=False is the actual blocker:
#    a 500 page renders request.META, which would contain the auth cookie.
python manage.py check --deploy --fail-level WARNING   # must exit 0

# 2. The characterization suite exists and passes. NOTE: use the full module
#    path -- `applications.globals.tests` fails unittest discovery because
#    applications/globals has no __init__.py (20 of 33 apps do not; that is
#    the project's existing state, not something this change alters).
#    pytest is deliberately NOT a dependency (CONTRIBUTING.md), so this runs
#    on Django's own test runner.
DJANGO_SETTINGS_MODULE=Fusion.settings.test \
  python manage.py test applications.globals.tests.test_auth_contract -v 2 --noinput

# 3. The index + the H3 field widening, both as migrations.
#    globals/0007 widens ExtraInfo.last_selected_role 20 -> 64.
#    globals/0008 adds ocms_grades_roll_sem_idx CONCURRENTLY (atomic=False).
python manage.py migrate globals
```

> Two indexes that an earlier draft of this runbook created by hand have been dropped after measurement —
> see [legacy-compatibility-and-erp-projection.md](legacy-compatibility-and-erp-projection.md#part-6--prerequisites-that-are-not-optional).
> Only `ocms_grades_roll_sem_idx` survives, and it now ships as a migration rather than a manual `psql`
> step.

**Checklist**

- [ ] `DEBUG = False` in production; no traceback page on a forced 500
- [ ] `SECRET_KEY`, DB credentials, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` all from env
- [ ] `CORS_ORIGIN_ALLOW_ALL` removed
- [ ] `CACHES` → Redis; `SESSION_ENGINE` → cache; `SESSION_SAVE_EVERY_REQUEST` dropped
- [ ] Three indexes created; login p95 recorded before and after
- [ ] Characterization suite green in CI
- [ ] Verified backup of `fusion_newui_prod` **restored on a scratch host** and timed

**Do not proceed if any box is unchecked.** In particular, `DEBUG = True` plus a `Path=/` cookie means the
next unhandled exception publishes a working credential.

---

## Phase 2 — Import users, shadow mode

`fusion-iam` is deployed with **nothing depending on it**.

```bash
# 1. Dry run first. Reports counts and every anomaly; writes nothing.
python manage.py import_legacy_identity --dry-run --report /tmp/import-report.json

# Expect roughly:
#   users 3277 · designations 40-60 · holds_designation ~6000 · module_access ~50
# Investigate before proceeding:
#   - users with no ExtraInfo row
#   - HoldsDesignation rows where user != working (become kind=officiating)
#   - designations with no ModuleAccess row
#   - designation names longer than 20 chars (H3)
#   - ModuleAccess rows whose designation matches no Designation (orphans)

# 2. Import. Password hashes are COPIED VERBATIM (algo=pbkdf2_sha256) and
#    transparently upgraded to Argon2id on each user's next successful login.
#    Nobody resets a password.
python manage.py import_legacy_identity --commit

# 3. Reconcile the H2 column drift into real monolith migrations, so
#    makemigrations stops wanting to drop production columns.
python manage.py generate_h2_alignment_migration   # emits an AddField migration; review, then apply
```

### The gate

```bash
# Nightly. Recomputes IAM's accessible_modules for every user and diffs it
# against the live legacy /api/auth/me output.
python manage.py iam_diff_module_access --days 7
```

**Gate: seven consecutive days of empty diffs.** Not "mostly empty".

Must be in the sample:

- a user with 3+ designations
- a user with **zero** `HoldsDesignation` rows — the legacy middleware's `designation[0]` `IndexError` case
- a user whose designation has no `ModuleAccess` row — the `access_rights` `UnboundLocalError` case
- a user whose designation name exceeds 20 characters
- an officiating holder (`user != working`)

**Rollback:** `systemctl stop fusion-iam`. Nothing depends on it. No data anywhere else has changed.

---

## Phase 3 — Dual auth (the risky one)

### Order matters — validators before issuer

```
1. Deploy IamJWTAuthentication to legacy and sysadmin, flags OFF.        (no behaviour change)
2. Deploy the shell at /app/, IAM_LOGIN_ENABLED off.                     (shell loads, login → legacy)
3. Turn on IAM_JWT_AUTH_ENABLED in legacy + sysadmin.                    (they now accept both)
4. Turn on IAM_LOGIN_ENABLED for the pilot group only.                   (IAM starts issuing)
```

Never reverse 3 and 4. Issuing tokens nothing can validate produces a broken pilot with no clean rollback
point.

### Pilot group

Placement staff (~5) plus one batch (~60 students). Enough to exercise both a student and a coordinator
path; small enough to phone everyone.

Selected by an explicit `identity_user` flag, not by role — so it can be changed without touching RBAC.

### Verification, before widening

```bash
# The critical assertion: byte-identical legacy contract, run against staging.
pytest applications/globals/tests/test_auth_contract.py::test_iam_me_matches_legacy_me -v
```

**Manual, by a human, in a browser:**

- [ ] Log in at `/app/` → sidebar shows exactly the expected modules
- [ ] Deep-link to a legacy academic page → recognized, not redirected to login
- [ ] `document.cookie` shows `fusion_csrf` only — **not** `fusion_at` or `fusion_rt`
- [ ] Log in with an old DRF token flow at the legacy login → still works
- [ ] Switch role in the shell → sidebar changes, legacy `/api/auth/me` reflects it within 30 s
- [ ] Log out → both applications reject the next request
- [ ] Two tabs, different roles → they do not interfere
- [ ] Idle 30 minutes → logged out of both

**Watch for 48 hours:** `iam_login_total{outcome}` · `iam_refresh_reuse_detected_total` (should be ~0; a
non-zero value means the client's single-flight refresh is broken) · legacy 401 rate · `outbox_lag_seconds`.

### Rollback

```bash
# ~30 seconds, and nobody has to log in again.
sed -i 's/IAM_JWT_AUTH_ENABLED=1/IAM_JWT_AUTH_ENABLED=0/' /etc/fusion/legacy.env
systemctl restart fusion fusion-sysadmin
# Shell: set IAM_LOGIN_ENABLED=0 → /app/login redirects to the legacy login.
```

Existing DRF tokens were never invalidated, so users continue on the legacy path uninterrupted.

---

## Phase 4 — IAM becomes the writer

**Blocked on the H1 decision.** Do not start without a written answer from the academic office on
multi-holder designations — see
[legacy-compatibility-and-erp-projection.md](legacy-compatibility-and-erp-projection.md#h1--only-one-holder-per-designation-institute-wide).

```bash
# 1. Reconciler in report mode for 7 days first.
python manage.py reconcile_erp_projection --mode report      # must show 0 drift, 7 consecutive days

# 2. Retire the console's write endpoints (they return 410 Gone; the UI points at the shell).
#    api/views/roles.py: update_user_roles, modify_moduleaccess, add_designation

# 3. IAM becomes the sole writer.
#    IAM_IS_ROLE_WRITER=1 ; systemctl restart fusion-iam-worker@iam

# 4. Reconciler to enforce.
python manage.py reconcile_erp_projection --mode enforce
```

**Gate:** a role change in the shell appears in legacy `/api/auth/me` within 30 seconds, and
`reconcile_erp_projection` reports zero drift for 7 consecutive days.

**Rollback:** `IAM_IS_ROLE_WRITER=0`. The projector pauses; events accumulate in `outbox_event` and drain
when it is re-enabled — idempotent, nothing lost. Re-enable the console's write endpoints.

---

## Phase 5+ — Retiring legacy auth

Two waits, both deliberate, both long.

```
Phase 4 stable for 30 days
  └─► LEGACY_LOGIN_ENABLED=0        # /api/auth/login/ returns 410; the legacy login page redirects to /app/
        └─► stable for a further 30 days
              └─► scramble auth_user.password to '!' for human users
```

**Do not compress these.** The second wait exists because scrambling the password column is the only
irreversible step in the entire migration. Until it happens, a full rollback to legacy authentication is
possible at any moment.

Before scrambling: verified backup, restored and checked on a scratch host, retained indefinitely.

---

## Incident: users cannot log in

Full procedure in [incident-auth-outage.md](../07-ops/runbooks/incident-auth-outage.md). Triage order:

```bash
systemctl status fusion-iam
curl -s localhost/app/api/iam/v1/../readyz            # DB + Redis + JWKS
curl -s https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq '.keys | length'   # expect 2
redis-cli -p 6379 ping                                # cache
redis-cli -p 6380 ping                                # broker
journalctl -u fusion-iam --since '10 min ago' | grep -E 'ERROR|CRITICAL'
```

| Symptom | Likely cause | Action |
|---|---|---|
| All logins fail, IAM up | signing key unreadable | check `LoadCredential`; [rotate-signing-key.md](../07-ops/runbooks/rotate-signing-key.md) |
| Logins succeed, every API 401 | JWKS not reachable by validators, or `aud` mismatch | check the JWKS proxy cache; verify `IAM_AUDIENCE` per service |
| Mass logouts, `refresh_reuse` spiking | client single-flight refresh broken | roll back the frontend; do **not** disable reuse detection |
| Only new users fail | `auth_user` projection failing | check `outbox_pending_rows`; user creation is the one synchronous projection |
| Only some roles wrong | projector paused or lagging | `outbox_lag_seconds`; `reconcile_erp_projection --mode report` |

**The escape hatch, at any point:** set `IAM_JWT_AUTH_ENABLED=0` and `IAM_LOGIN_ENABLED=0`. Everyone falls
back to legacy authentication with their existing tokens intact. This works right up until
`LEGACY_LOGIN_ENABLED` is turned off, which is why that flag waits 30 days past Phase 4.

---

## Communications

| When | Audience | Message |
|---|---|---|
| Phase 3 −7 days | pilot group | You are piloting a new login at `/app/`. The old one still works. Here is who to contact. |
| Phase 3 −1 day | IT helpdesk | Both logins are valid. Symptoms to escalate, and the rollback is a flag flip. |
| Phase 3 +0 | pilot group | It is live. Report anything odd, however small. |
| Before widening | all users | New login page, one password, unchanged. Screenshot included. |
| Phase 4 −7 days | academic office, placement office | Role administration moves to `/app/`. **Secondary/scoped role holders will not appear in the old sidebar** (H1) — this is expected, not a bug. |
| `LEGACY_LOGIN_ENABLED=0` −14 days | all users | The old login page retires on `<date>`. Bookmark `/app/`. |

The Phase 4 note to the placement and academic offices matters. Without it, H1's known limitation arrives
as a bug report during a placement season.
