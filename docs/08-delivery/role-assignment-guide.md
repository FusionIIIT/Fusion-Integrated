---
Purpose: >
  How to declare a new role for your module, grant it access, put a test
  account into it, and log in as that account. Companion to
  student-assignment-guide.md — read that one first for environment setup.
---

# Declaring and assigning a role

Your module needs people to hold roles beyond the three basic ones (student,
faculty, staff) that come automatically from the ERP. This guide is the
complete path from "I need a role called X" to "I am logged in as X and can
see my module."

There are two separate things happening here, and mixing them up is the most
common confusion:

1. **Declaring a role** — your own work, in your module's code. States that
   the role exists and what it may do.
2. **Assigning a role** — a one-off action against a test account, so you
   personally can log in and see what that role sees. Nobody does this in
   production; the real ERP's designation data does it automatically.

## Prerequisites

- You've followed `student-assignment-guide.md` Step 3 and have both
  `Fusion_System_Administrator` and `Fusion-Integrated` running, `fusionlab`
  restored from `fusion-dev.dump`, and `manage.py sync_identity` has run at
  least once.
- You know your module's directory name (`modules/<your_module>/`).

Every `manage.py` command below for `Fusion_System_Administrator` is run from:

```bash
cd Fusion_System_Administrator/Backend/backend
```

using `./../venv/bin/python manage.py ...` — not a bare `python`, because the
project's dependencies live in `Backend/venv`, one level above this directory.

---

## Step 1 — Declare the role in your module's `registry.py`

Open `modules/placement/registry.py` in `Fusion-Integrated` first — it's the
reference module, and the shape you need is already there:

```python
#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    # ...
]

_OFFICER = [
    "placement_cell.job_posting.view",
    "placement_cell.job_posting.manage",
    "placement_cell.application.review",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement_officer": _OFFICER,
}
```

**A role is created the moment its name appears as a key in `ROLE_GRANTS`.**
There is no separate registration step, no model row to create by hand — the
dict key *is* the role.

Copy that shape into your own `modules/<your_module>/registry.py`. For an
Employee Leave Management module, that might look like:

```python
PERMISSIONS = [
    ("leave_elm.application.view", "See leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.approve", "Approve or reject a leave application"),
]

_EMPLOYEE = ["leave_elm.application.view", "leave_elm.application.apply"]
_APPROVER = ["leave_elm.application.view", "leave_elm.application.approve"]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
}
```

The role name (`"Leave Approver"`) is free text — it does not need to exist
anywhere else first. You do not need to register it with the IAM team or edit
any file outside your own module.

If your module also has screens, declare `MODULE` and `NAV_ITEMS` the same way
`placement/registry.py` does — see that file for the full shape, including
`required_permission` on each nav item. A module with no screens yet (pure
API) can skip `NAV_ITEMS`.

## Step 2 — Generate and publish the manifest

`registry/permissions.json` is generated, never hand-edited. It is built by
scanning every module's `registry.py`:

```bash
cd Fusion-Integrated
make permissions
```

This **fails on purpose** if something is wrong — a permission declared in
`PERMISSIONS` but granted to nobody in `ROLE_GRANTS`, or granted but never
declared, or missing your module's own prefix. Fix the error it reports
before moving on; it is telling you about a real gap, not a formality.

Once it succeeds, publish it to the IAM:

```bash
cd ../Fusion_System_Administrator/Backend/backend
./../venv/bin/python manage.py seed_iam_permissions \
  --manifest /full/path/to/Fusion-Integrated/registry/permissions.json
```

At this point the role **exists and has permissions**, but nobody holds it
yet.

## Step 3 — Find a test account (optional)

The dump's usernames are already sequential and self-explanatory
(`fac00001`, `stu00001`, `staff00001`, ...) — you can skip straight to Step 4
with any one of them. This step just helps you see what is available:

```bash
./../venv/bin/python manage.py find_user --kind faculty --limit 50
./../venv/bin/python manage.py find_user --kind staff --limit 50
```

`--q` narrows by username or display name, e.g. `--q nair`, but is not
required — running with just `--kind` lists everyone of that kind.

## Step 4 — Put a specific account into the role

```bash
./../venv/bin/python manage.py assign_role --user fac00005 --designation "Leave Approver"
```

`--user` takes a username or an `erp_user_id`. Run it again with `--remove`
to take the role away:

```bash
./../venv/bin/python manage.py assign_role --user fac00005 --designation "Leave Approver" --remove
```

This writes directly — it does not check whether `"Leave Approver"` is a
"real" institute role, because for your own module's designations it never
will be. An unrecognised designation is allowed by design (see
`iam/rbac.py`'s own docstring): only the institute's existing office/rank
roles (Dean Academic, HOD, and so on) are catalogued, and that catalogue is
an audit list, not a gate.

## Step 5 — Log in and verify

Open the client (`http://localhost:5173`), sign in with the username from
Step 3/4 and password **`fusion123`** (every dump account shares it). Use the
role switcher to select the new role, and confirm your module appears.

**If you were already logged in before Step 4**, log out and back in. The
client caches your session for 60 seconds
(`IAM_SESSION_CACHE_SECONDS`), so a role assigned mid-session will not appear
until that cache expires or you force a fresh login.

---

## Quick reference

| Command | Where | What it does |
|---|---|---|
| `make permissions` | `Fusion-Integrated` | Regenerate `registry/permissions.json` from every module's `registry.py` |
| `manage.py seed_iam_permissions --manifest <path>` | IAM | Publish that manifest's designation → permission/module grants |
| `manage.py find_user --kind <kind> [--q <text>]` | IAM | Browse or search synced accounts by kind/name/username |
| `manage.py assign_role --user <u> --designation <d> [--remove]` | IAM | Grant or revoke one designation on one account |

## Common mistakes

- **Editing `registry/permissions.json` by hand.** It is overwritten by
  `make permissions` on the next run. Edit `registry.py` instead.
- **Running `seed_iam_permissions` without regenerating the manifest first.**
  Your new role will not be in the file yet — run `make permissions` in
  `Fusion-Integrated` before `seed_iam_permissions` in the IAM.
- **Testing without a role switch.** Holding a designation is not the same as
  *acting* as it — select it in the role switcher after logging in.
- **Expecting a role change to show up instantly** in an already-open
  session. See the 60-second cache note in Step 5.
