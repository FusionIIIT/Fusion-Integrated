# Runbook — Unlock an Account

**Time:** ~2 min. **Risk:** low, but **verify the identity of the requester first** — an unlock request is a
plausible social-engineering vector.

```bash
cd /srv/fusion/iam/current
MANAGE="sudo -u fusion venv/bin/python manage.py"
U=22bcs001
```

---

## 1. Establish what is actually wrong

"I can't log in" has several distinct causes, and only one of them is a lockout.

```bash
$MANAGE account_status --username "$U"
```

```
username        22bcs001
status          active
mfa_required    false
locked          yes  (until 2026-08-01T10:34:00Z, tier 3 of 4)
failures        11 in the last hour  (username: 11, ip 10.2.3.4: 14)
last success    2026-07-30T09:12:00Z
sessions        0 active
erp_user_id     1234   (auth_user present ✔)
credential      argon2id, changed 2026-01-14, must_change=false
```

| Reading | Meaning | Go to |
|---|---|---|
| `locked yes` | too many failed attempts | §2 |
| `status suspended` / `archived` | an administrative action, **not** a lockout | §3 |
| `must_change true` | a forced reset is pending | §4 |
| `mfa_required true`, no confirmed factor | enrolment never completed | §5 |
| `erp_user_id` null | the ERP projection never landed | §6 |
| Nothing wrong here | not an account problem | §7 |

---

## 2. A genuine lockout

Progressive lockout: 5 failures → 60 s · 8 → 5 min · 10 → 30 min · **15 → admin unlock required**. Counted per
**username and per IP**, whichever trips first.

### Verify the requester

Before unlocking, confirm identity through a channel **other than** the one the request arrived on: institute
email to the address on file, a phone call to the recorded number, or in person at the office.

An unlock request by chat or from an unfamiliar address, referencing only a username, is exactly what an
attacker sends after a failed credential-stuffing run. The `failures` and IP counts above are the tell — many
failures from one unfamiliar IP is not a forgetful user.

```bash
$MANAGE unlock_account --username "$U" --reason "verified by phone, ticket #4412"
```

This clears the username counter and writes an `audit_event`. `--reason` is required.

### If the IP is the problem

Note the distinction: unlocking the username does not clear an IP-level block, which is deliberate — a shared
lab machine can lock out a whole room.

```bash
$MANAGE unlock_ip --ip 10.2.3.4 --reason "shared lab machine, ticket #4412"
```

**Do not clear an IP block when the failures look like an attack.** Ask the user to try from another network
instead.

---

## 3. Suspended or archived

This is not a lockout. Someone deliberately disabled the account, and there is an audit trail:

```bash
$MANAGE shell -c "
from auditing.models import AuditEvent
for e in AuditEvent.objects.filter(target_type='identity_user', target_id='$U',
                                   action__contains='status').order_by('-at')[:5]:
    print(e.at, e.action, e.actor_user_id, e.before, '->', e.after)
"
```

Reactivation needs the authority of whoever suspended the account — usually the academic office (for a student)
or HR (for staff). **Do not reactivate on a helpdesk request.**

```bash
$MANAGE set_user_status --username "$U" --status active --reason "reinstated, approved by <name>, ticket #…"
```

An archived graduate is a different case: they are archived by policy, and reactivation is an exception that
needs a named approver.

---

## 4. `must_change` is set

The account is fine; the user must set a new password before proceeding. Point them at the self-service reset
rather than setting one for them:

```
https://fusion.iiitdmj.ac.in/app/login → "Forgot password"
```

The OTP flow (10-minute TTL, 5 attempts, 3 per hour) is a faithful port of the legacy monolith's, which is
well built. Self-service means no operator ever handles a password.

If the user cannot receive the OTP (wrong email on file), fix the email first — then let them reset. **Never
set a password on someone's behalf**; it puts a known credential in an operator's hands and in a chat log.

---

## 5. MFA problems

```bash
$MANAGE mfa_status --username "$U"
```

| Situation | Action |
|---|---|
| Enrolment started, `confirmed_at` null | the factor does not count; the user re-enrolls at next login |
| Lost device, recovery code available | user enters a recovery code themselves |
| Lost device, no recovery codes | §5a — **in-person verification required** |
| TOTP codes rejected but the device works | clock skew — check `chronyd` on the server |

### 5a. Resetting MFA — in person only

`iam.mfa.manage` is `is_dangerous`: MFA + step-up re-auth ≤5 minutes, and every use is audited.

**Verify in person, with institute ID.** Resetting MFA removes the second factor from an account that holds
dangerous permissions — a remote reset on a phone call is precisely the attack this control exists to stop.

```bash
$MANAGE reset_mfa --username "$U" --reason "in-person ID verified by <operator>, ticket #4412"
```

The user re-enrolls at next login and receives fresh recovery codes. Tell them to store them somewhere that is
not the same phone.

---

## 6. `erp_user_id` is null

The account exists in IAM but the legacy monolith does not know them. User creation is the one **synchronous**
projection, so this means it failed at creation time.

```bash
journalctl -u 'fusion-iam-worker@iam' --since '2 days ago' | grep -i "$U"
$MANAGE project_user --username "$U"        # idempotent
```

If it fails again, the ERP write is blocked — check the `iam_erp_projector` grants and ERP availability.
→ [incident-auth-outage.md](incident-auth-outage.md) §7.

Symptom to expect: they can log in at `/app/` but the legacy academic app rejects them.

---

## 7. Nothing is wrong with the account

Then it is not an account problem:

```bash
$MANAGE login_attempts --username "$U" --limit 20
```

| Outcome recorded | Actually happening |
|---|---|
| `unknown_user` | they are typing the wrong username — often an email instead of a roll number |
| `bad_password` from one IP repeatedly | genuinely forgotten; send them to self-service reset |
| **no attempts at all** | the request never reached us — network, or they are on the wrong URL |
| `throttled` | rate-limited, not locked; wait a minute |
| `success` then immediate failure elsewhere | a session/cookie problem → [incident-auth-outage.md](incident-auth-outage.md) §5 |

"No attempts at all" is the common surprise. Check they are at `/app/` and not a bookmarked old URL.

---

## 8. Verify

```bash
$MANAGE account_status --username "$U"       # locked: no
```

- [ ] `locked no`, `status active`
- [ ] The user confirms they are in — **ask them, do not assume**
- [ ] An `audit_event` exists for whatever you did, with the ticket reference in `reason`

---

## 9. Notes

- **Every action here is audited.** `--reason` is mandatory on each command and should carry the ticket number
  and how identity was verified.
- Unlocking does **not** reset a password, change MFA, or create a session. It only clears the counter.
- `iam.mfa.manage` and `iam.credential.update` are `is_dangerous` and appear in the **weekly privileged-access
  review**. Expect your unlocks to be read.
- A spike in `iam_lockout_total` across many usernames is not a helpdesk matter — it is credential stuffing.
  Escalate rather than unlocking each account.
- If more than a handful of accounts are locked at once, stop and look for a common cause: an expired
  institute password sync, a bad bookmark circulating, or an attack.
