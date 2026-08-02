# Runbook — Incident: users cannot log in

**Severity: highest.** Nobody can use anything.

**The escape hatch, available at any point:** fall back to legacy authentication. Existing DRF tokens were never
invalidated, so this needs no re-login. It works right up until `LEGACY_LOGIN_ENABLED` is turned off — which is
why that flag waits 30 days past Phase 4.

```bash
sudo sed -i 's/^IAM_JWT_AUTH_ENABLED=1/IAM_JWT_AUTH_ENABLED=0/' /etc/fusion/legacy.env
sudo systemctl restart fusion
# Shell: set IAM_LOGIN_ENABLED=0 → /app/login redirects to the legacy login.
```

Take the escape hatch early if the cause is not obvious within 10 minutes. Diagnose afterwards.

---

## 1. Triage — 60 seconds

```bash
ssh fusion-vm

systemctl is-active fusion-iam fusion-platform fusion fusion-sysadmin
curl -s -o /dev/null -w 'iam readyz: %{http_code}\n'      localhost/app/api/iam/v1/readyz
curl -s -o /dev/null -w 'platform readyz: %{http_code}\n' localhost/app/api/platform/v1/readyz
curl -s https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq '.keys | length'   # expect 1 or 2
redis-cli -p 6379 ping        # cache
redis-cli -p 6380 ping        # broker
psql -h 127.0.0.1 -p 6432 -U platform_app -d fusion_nonacad -c 'select 1' >/dev/null && echo 'db ok'
df -h /var/lib/postgresql | tail -1

journalctl -u fusion-iam --since '10 min ago' | grep -E '"level":"(error|critical)"' | tail -20
```

---

## 2. Symptom → cause

| Symptom | Likely cause | Go to |
|---|---|---|
| IAM not running | crash on boot — usually a startup assertion | §3 |
| IAM up, **all** logins fail | signing key unreadable, or database | §4 |
| Login succeeds, **every** API call 401s | JWKS unreachable by validators, or `aud` mismatch | §5 |
| Mass logouts, `refresh_reuse` spiking | **the client's single-flight refresh broke** | §6 |
| Only **new** users fail | `auth_user` projection failing | §7 |
| Only **some** roles wrong | projector paused or lagging | §8 |
| Everything slow, then 502 | database or PgBouncer saturation | §9 |
| Only the legacy app fails | it is a legacy problem, not ours | §10 |

---

## 3. IAM will not start

```bash
journalctl -u fusion-iam -n 60 --no-pager
```

Startup assertions refuse to boot on a misconfiguration — deliberately, so the failure is loud rather than
subtle. Look for a `fusion.Exxx` code:

| Code | Meaning | Fix |
|---|---|---|
| `fusion.E001` | `ALLOWED_HOSTS` contains `*` | fix the env file |
| `fusion.E002` | cookies not `Secure` while `DEBUG=False` | fix the env file |
| `fusion.E003` | `SECRET_KEY` is a known dev value | set a real one |
| `fusion.E010/E011` | `CONN_MAX_AGE`/cursors wrong under PgBouncer | fix; **do not** bypass — it risks cross-request session state |
| `fusion.E020` | **broker Redis is not `noeviction`** | fix `redis-broker.conf`; an LRU broker silently drops tasks |
| `fusion.E030` | ERP connection is not the read-only role | fix the URL |
| `fusion.E031` | `search_path` wrong — IAM tables would land in the wrong schema | fix before starting |

Missing signing key:

```bash
sudo ls -la /etc/fusion/credentials/          # expect 0400 root:root
sudo systemctl cat fusion-iam | grep LoadCredential
```

---

## 4. All logins fail, IAM is up

```bash
curl -sS -X POST localhost/app/api/iam/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"x","password":"y"}' -i | head -20
```

| Response | Cause | Fix |
|---|---|---|
| 500 | signing key or database | check the log; §3 |
| 503 | database unreachable | §9 |
| 429 for everyone | throttle counters poisoned, or cache Redis restarted oddly | `redis-cli -p 6379 --scan --pattern 'throttle:*' \| xargs -r redis-cli -p 6379 DEL` |
| 401 for a **known-good** password | password verification broken — check `argon2-cffi` present in the release | reinstall dependencies or roll back |

```bash
psql -h 127.0.0.1 -p 6432 -U iam_app -d fusion_system_db \
  -c "select count(*) from iam.identity_user where status='active';"
```

If that count is 0, this is a data problem → [restore-from-backup.md](restore-from-backup.md).

---

## 5. Logins work, every API call 401s

Tokens are being minted but not accepted. Almost always JWKS or audience.

```bash
curl -s https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq '.keys[].kid'
grep -h IAM_ /etc/fusion/platform.env /etc/fusion/iam.env | sort
```

Check:

- [ ] The JWKS response lists the `kid` that new tokens carry.
- [ ] Each validator's `IAM_AUDIENCE` is in the token's `aud` array.
- [ ] `IAM_ISSUER` matches the `iss` claim **exactly** (trailing slashes count).

```bash
# Flush the validator caches, then nginx's proxy cache.
redis-cli -p 6379 --scan --pattern 'iam:jwks:*' | xargs -r redis-cli -p 6379 DEL
sudo systemctl restart nginx
```

**If this followed a key rotation, the order was wrong** — the signer was switched before validators had the new
public key. Revert `IAM_SIGNING_KID` to the previous value and `systemctl reload fusion-iam`; recovery is
immediate because the old public key is still published.
→ [rotate-signing-key.md](rotate-signing-key.md)

Also check that a `sid` is not wrongly denylisted:

```bash
redis-cli -p 6379 --scan --pattern 'iam:revoked_sid:*' | head
```

---

## 6. Mass logouts with `refresh_reuse` spiking

```bash
curl -s localhost:9102/metrics | grep iam_refresh_reuse_detected_total
```

A spike here **almost never means an attack**. It means the frontend's single-flight refresh broke: parallel 401s
each fire a refresh, nine present the same not-yet-rotated token, reuse detection fires, and the family is
revoked. A self-inflicted outage.

**Roll back the frontend.** Do **not** disable reuse detection — that would remove a real security control to
work around a client bug.

```bash
sudo -u fusion ln -sfn /srv/fusion/shell/releases/<previous-sha> /srv/fusion/shell/current
```

Then verify with a Playwright test that ten parallel requests on an expired token produce exactly one refresh
call, before shipping the frontend again.

---

## 7. Only new users cannot log in

User creation is the **one** synchronous projection: `identity_user` plus an `auth_user` row in the ERP
([ADR-0002](../../01-architecture/adr/0002-separate-iam-service-and-database.md)). If the ERP write fails, the
user exists in IAM but the legacy monolith does not know them.

```bash
psql -h 127.0.0.1 -p 6432 -U iam_app -d fusion_system_db -c \
  "select count(*) from iam.identity_user where erp_user_id is null and kind <> 'service';"
```

Non-zero means projection failures. Check the projector's grants and the ERP's availability:

```bash
journalctl -u 'fusion-iam-worker@iam' --since '30 min ago' | grep -i projection
```

---

## 8. Some roles are wrong

```bash
cd /srv/fusion/iam/current
sudo -u fusion venv/bin/python manage.py reconcile_erp_projection --mode=report
grep IAM_IS_ROLE_WRITER /etc/fusion/iam.env
curl -s localhost:9101/metrics | grep outbox_lag_seconds
```

If the projector is paused, events are **queued, not lost** — they drain when it is re-enabled. If drift is
real and understood:

```bash
sudo -u fusion venv/bin/python manage.py reconcile_erp_projection --mode=enforce
```

**Do not run `--mode=enforce` on drift you do not understand.** It overwrites the ERP.

Note: reported drift matching an `IntentionalProjectionGap` (H1 multi-holder roles) is **expected** and is not
counted.

---

## 9. Slow, then 502

```bash
psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY 2;"
psql -c "SELECT pid, now()-query_start AS age, left(query,80) FROM pg_stat_activity
         WHERE state='active' ORDER BY age DESC LIMIT 5;"
psql -h 127.0.0.1 -p 6432 -U pgbouncer pgbouncer -c 'SHOW POOLS;'
```

`statement_timeout = 30s` should be killing pathological queries. If a query is older than that, the timeout is
not applied to that role — check it.

```bash
# Last resort, and it aborts a transaction:
psql -c "SELECT pg_cancel_backend(<pid>);"
```

Check the disk. It is the one failure that corrupts rather than degrades:

```bash
df -h /var/lib/postgresql
```

---

## 10. Only the legacy app fails

Not our incident, but check we did not cause it:

```bash
sudo nginx -t
curl -s -o /dev/null -w '%{http_code}\n' https://fusion.iiitdmj.ac.in/api/auth/me    # expect 401
sudo journalctl -u fusion --since '15 min ago' | tail -40
```

A new `location` block can shadow `/`. This is precisely why every deploy smoke-tests the legacy endpoint.

---

## 11. Communicate

| When | Say |
|---|---|
| Within 5 min | "Login is affected. Investigating. Next update in 15 minutes." |
| Every 15 min | what is known, what is being tried, ETA if any |
| On fallback | "Please use the old login page at `/accounts/login`. Your account is unaffected." |
| Resolved | what happened, whether any data was affected, what changes next |

Do not speculate about cause while users are waiting. Say what is known.

---

## 12. Afterwards

- Timeline: first symptom → detection → mitigation → resolution. Detection time is usually the number worth
  improving.
- **Which alert fired?** If none did, that is the primary finding — add it.
- The deliverable is the **test or assertion** that would have caught it, not the write-up.
- If the runbook was wrong or slow, fix this file the same day.
- If the escape hatch was used, confirm it worked as documented; if it did not, that is the highest-priority
  follow-up.
