---
Purpose: >
  Everything from a fresh machine to logging in as a test account holding a
  role you defined yourself: environment setup, declaring a role in your
  module's registry.py, publishing it, assigning it to a test account, and
  verifying the login. Every step past Part 1 has been run end to end against
  a clean fusion-dev.dump restore, for all three basic kinds (student,
  faculty, staff) — see "Proof this works" at the bottom.
---

# Full setup guide: environment, roles, and login

There are two separate things in this guide, and mixing them up is the most
common confusion:

1. **Part 1 — get the environment running.** One-time setup: install
   dependencies, restore the shared dump, bring both services up.
2. **Part 2 onward — declare and test your own role.** Your own work, repeated
   every time your module needs a new role: state that it exists, publish it,
   put a test account into it, log in as that account.

---

## Part 1 — Get the environment running

Full, exact, OS-specific commands live in `Fusion-README` — follow whichever
one matches your machine, start to finish, before continuing to Part 2:

- **Windows / WSL or native Ubuntu:** [`QUICKSTART.md`](https://github.com/FusionIIIT/Fusion-README/blob/main/QUICKSTART.md)
- **macOS:** [`QUICKSTART-macOS.md`](https://github.com/FusionIIIT/Fusion-README/blob/main/QUICKSTART-macOS.md)
- **Anything that doesn't fit either** (different OS, something already partly
  set up): [`Fusion_System_Setup.md`](https://github.com/FusionIIIT/Fusion-README/blob/main/Fusion_System_Setup.md)

What those guides take you through, so you know what "done" looks like:

1. Install Postgres, Python, Node, and the other tools.
2. Restore `fusion-dev.dump` into a database called `fusionlab` — this is the
   shared synthetic dataset (3277 accounts: `stuNNNNN` / `facNNNNN` / staff
   accounts, every one sharing the password **`fusion123`**). Nothing in it is
   a real person.
3. Clone and configure both `Fusion_System_Administrator` (the IAM — identity,
   login, roles) and `Fusion-Integrated` (the platform your module lives in).
4. Migrate both services' databases and run `manage.py sync_identity` once,
   which copies the dump's accounts into the IAM's own tables.
5. Start the IAM, start `Fusion-Integrated`'s backend (`make dev`), start its
   client (`cd client && npm run dev`).
6. Confirm you can log in at `http://localhost:5173` with one of the dump's
   `stuNNNNN` accounts and see `Placement Cell` (the reference module) in the
   sidebar.

Do not continue to Part 2 until that last checkbox is true. If it isn't, the
problem is in your environment, not in anything below — go back to the
Fusion-README guide and `docs/08-delivery/student-assignment-guide.md`'s own
Step 3 checklist.

**One thing worth knowing up front:** your own local `fusionlab` may drift
from the public dump over time (re-syncs, manual edits, whatever you've done
to it) — the usernames and even the shared `fusion123` password are a property
of a *clean* `fusion-dev.dump` restore specifically. If a login ever fails
unexpectedly, that's the first thing to suspect, not the commands in this
guide.

---

## Part 2 — Declare the role in your module's `registry.py`

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

## Part 3 — Generate and publish the manifest

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

Once it succeeds, publish it to the IAM. Every command from here on is run
from:

```bash
cd Fusion_System_Administrator/Backend/backend
```

using `./../venv/bin/python manage.py ...` — not a bare `python`, because the
project's dependencies live in `Backend/venv`, one level above this directory.

```bash
./../venv/bin/python manage.py seed_iam_permissions \
  --manifest /full/path/to/Fusion-Integrated/registry/permissions.json
```

At this point the role **exists and has permissions**, but nobody holds it
yet.

## Part 4 — Find a test account (optional)

The dump's usernames are already sequential and self-explanatory
(`facNNNNN`, `stuNNNNN`, and a staff pattern you'll see once you look) — you
can skip straight to Part 5 with any one of them. This step just helps you
see what is available:

```bash
./../venv/bin/python manage.py find_user --kind faculty --limit 50
./../venv/bin/python manage.py find_user --kind staff --limit 50
./../venv/bin/python manage.py find_user --kind student --limit 50
```

`--q` narrows by username or display name, e.g. `--q nair`, but is not
required — running with just `--kind` lists everyone of that kind.

## Part 5 — Put a specific account into the role

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
an audit list, not a gate. This also means **any basic kind can hold any role
you invent** unless your own module's design says otherwise — a student
holding "Leave Approver" is not blocked by the platform.

## Part 6 — Log in and verify

Open the client (`http://localhost:5173`), sign in with the username from
Part 4/5 and password **`fusion123`** (every dump account shares it). Use the
role switcher to select the new role, and confirm your module appears.

**If you were already logged in before Part 5**, log out and back in. The
client caches your session for 60 seconds (`IAM_SESSION_CACHE_SECONDS`), so a
role assigned mid-session will not appear until that cache expires or you
force a fresh login.

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
  session. See the 60-second cache note in Part 6.
- **Assuming your personal working database behaves like a clean restore.**
  If you've been experimenting for a while, your `fusionlab` may no longer
  match a fresh `fusion-dev.dump` — if logins start failing for no obvious
  reason, restore a clean copy into a throwaway database name and compare,
  rather than debugging against drifted data.

## Proof this works

Run end to end against a genuinely clean `fusion-dev.dump` restore (not a
personal working database), for all three basic kinds, using the reference
`placement` module's own roles:

| Account kind | Username pattern | Designation assigned | Login | Roles returned | Modules returned |
|---|---|---|---|---|---|
| Faculty | `facNNNNN` | `placement_coordinator` | OK | `student`-equivalent gate N/A | `directory`, `placement_cell` |
| Staff | `stfNNNNN` | `placement_officer` | OK | `staff`, `placement_officer` | `directory`, `placement_cell` |
| Student (no extra role) | `stuNNNNN` | — (basic kind only) | OK | `student`, `ug_student` | `placement_cell` |
| Student (with an extra role) | `stuNNNNN` | `placement_coordinator` | OK | `student`, `placement_coordinator` | `directory`, `placement_cell` |

Every row used a throwaway scratch database, dropped immediately after — this
guide's commands do not require touching anyone's personal working database
to verify.
