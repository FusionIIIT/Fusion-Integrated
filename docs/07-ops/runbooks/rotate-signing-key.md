# Runbook — Rotate the IAM Signing Key

**Time:** ~20 min (15 of which is waiting). **Risk:** low if the order is followed — **total auth outage if it
is not.**

Two keys live at once, selected by the JWT `kid` header. That is what makes this zero-downtime.

```bash
KEYDIR=/etc/fusion/credentials
NEW_KID=$(date +%Y%m)          # e.g. 202608
```

**Routine:** quarterly. **Emergency:** suspected compromise — §5.

---

## The rule

**Publish the new public key. Wait for every validator's JWKS cache to expire. Only then switch the signer.**

Switching the signer first mints tokens that no validator can verify, and every request 401s until the caches
expire. There is no fast recovery from that; you simply wait out the TTL.

JWKS TTL is 10 minutes (Redis in each service, plus `proxy_cache_valid 200 10m` in nginx). **Wait 15.**

---

## 1. Generate

```bash
sudo -u root openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$KEYDIR/iam_signing_$NEW_KID.pem"
sudo chmod 400 "$KEYDIR/iam_signing_$NEW_KID.pem"
sudo chown root:root "$KEYDIR/iam_signing_$NEW_KID.pem"

sudo openssl rsa -in "$KEYDIR/iam_signing_$NEW_KID.pem" -pubout \
  -out "$KEYDIR/iam_signing_$NEW_KID.pub"
```

RSA 2048 for RS256. Keys are delivered via systemd `LoadCredential=`, never an env var — so they never appear
in `/proc/<pid>/environ`.

---

## 2. Publish the new public key (signer unchanged)

```bash
sudo tee -a /etc/fusion/iam.env >/dev/null <<EOF
IAM_NEXT_KID=$NEW_KID
IAM_NEXT_PUBLIC_KEY_PATH=$KEYDIR/iam_signing_$NEW_KID.pub
EOF

sudo systemctl reload fusion-iam
```

```bash
# JWKS should now advertise TWO keys. Tokens are still signed by the OLD kid.
curl -fsS https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq '.keys[].kid'
```

- [ ] Two `kid` values listed
- [ ] Logins still work
- [ ] No change in the 401 rate

---

## 3. Wait 15 minutes

Not optional, and not shortenable. Every validator — platform, legacy monolith, sysadmin console — plus the
nginx proxy cache must have picked up the new key.

```bash
sleep 900
sudo systemctl restart nginx      # optional: flush the JWKS proxy cache early
```

---

## 4. Switch the signer

```bash
sudo sed -i "s|^IAM_SIGNING_KID=.*|IAM_SIGNING_KID=$NEW_KID|" /etc/fusion/iam.env
sudo sed -i "s|^IAM_SIGNING_KEY_PATH=.*|IAM_SIGNING_KEY_PATH=$KEYDIR/iam_signing_$NEW_KID.pem|" \
  /etc/fusion/iam.env
# Keep the OLD public key published — unexpired tokens are still signed with it.
sudo sed -i "s|^IAM_PREVIOUS_KID=.*|IAM_PREVIOUS_KID=<old_kid>|" /etc/fusion/iam.env

sudo systemctl reload fusion-iam
```

### Verify immediately

```bash
# A fresh token must carry the new kid.
curl -sS -X POST localhost/app/api/iam/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"'"$SMOKE_USER"'","password":"'"$SMOKE_PASS"'"}' \
  -c /tmp/c.txt -o /dev/null
python3 - <<'PY'
import base64, json, re, pathlib
tok = re.search(r'fusion_at\s+(\S+)', pathlib.Path('/tmp/c.txt').read_text()).group(1)
h = tok.split('.')[0] + '=='
print("kid:", json.loads(base64.urlsafe_b64decode(h))["kid"])
PY
rm -f /tmp/c.txt
```

```bash
# And that token is accepted by the platform and the legacy app.
curl -fsS -b "fusion_at=$TOK" localhost/app/api/platform/v1/healthz
curl -s -o /dev/null -w '%{http_code}\n' -b "fusion_at=$TOK" localhost/api/auth/me   # expect 200
```

- [ ] New tokens carry `NEW_KID`
- [ ] Tokens are accepted by platform **and** legacy
- [ ] 401 rate unchanged
- [ ] `iam_login_total{outcome="success"}` still rising

**If 401s spike:** revert `IAM_SIGNING_KID` to the old value and `systemctl reload fusion-iam`. Recovery is
immediate, because the old public key is still published.

---

## 5. Retire the old key

Wait **one access-token lifetime plus a margin** — 30 minutes — so no unexpired token is signed by the old key.

```bash
sleep 1800
sudo sed -i '/^IAM_PREVIOUS_KID=/d;/^IAM_NEXT_KID=/d;/^IAM_NEXT_PUBLIC_KEY_PATH=/d' /etc/fusion/iam.env
sudo systemctl reload fusion-iam
curl -fsS https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq '.keys|length'   # expect 1
```

Keep the old private key offline for 90 days (for forensic verification of historical tokens), then destroy it.

---

## 6. Emergency rotation — suspected compromise

A compromised signing key lets an attacker mint valid tokens **for any user, on every service**. This is the
single highest-consequence secret in the system.

Accept the outage; do **not** wait 15 minutes.

```bash
# 1. Generate and switch in one step.
#    Every existing token becomes invalid. Every user must log in again.
sudo sed -i "s|^IAM_SIGNING_KID=.*|IAM_SIGNING_KID=$NEW_KID|;
             s|^IAM_SIGNING_KEY_PATH=.*|IAM_SIGNING_KEY_PATH=$KEYDIR/iam_signing_$NEW_KID.pem|;
             /^IAM_PREVIOUS_KID=/d" /etc/fusion/iam.env
sudo systemctl restart fusion-iam nginx

# 2. Revoke every session, so no refresh token can mint a new access token either.
cd /srv/fusion/iam/current
sudo -u fusion venv/bin/python manage.py revoke_all_sessions --reason=key_compromise

# 3. Flush validator caches.
redis-cli -p 6379 --scan --pattern 'iam:jwks:*' | xargs -r redis-cli -p 6379 DEL
sudo systemctl restart fusion-platform fusion fusion-sysadmin
```

Then: notify all users that they must log in again · audit `audit_event` for the compromise window · rotate
`DJANGO_SECRET_KEY` and database passwords as well if the host itself may be compromised · write it up.

---

## 7. Notes

- Rotating `FERNET_KEY` is a **different, harder** procedure — it requires re-encrypting every
  `identity_mfa_factor.secret_enc` and is **not** zero-downtime. Do not conflate the two.
- `DJANGO_SECRET_KEY` rotation invalidates Django sessions but **not** IAM tokens (which are RS256-signed).
  Annual, low impact for the new services.
- Cadence: signing key quarterly · `DJANGO_SECRET_KEY` annually · database passwords annually ·
  `FERNET_KEY` only on suspected compromise.
- Log the rotation in the ops journal with date, old `kid`, new `kid`, and who performed it.
