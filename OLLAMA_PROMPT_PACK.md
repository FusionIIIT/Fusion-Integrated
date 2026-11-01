# Ollama Prompt Pack — ELM Phase 2 (Fusion-Integrated)

If a step fails twice, start a FRESH Ollama session with just that step's prompt
(every prompt below is self-contained on purpose — small models lose context fast).

**Repo facts every prompt repeats (so the model never guesses):**
- Repo root: `/home/atharva/Documents/Fusion/Fusion-Integrated` — Django 4 + DRF + React.
- Module: `modules/leave/` — layers: `domain/` (pure), `services/`, `selectors/`, `api/`,
  plus `models.py`, `registry.py`, `contracts.py`, `apps.py`.
- Reference module (fully working — copy its patterns): `modules/placement/`.
- Python: `.venv/bin/python` · checks: `make check` (see Makefile).
- Specs (plain text): `04_ELM_Business_Rule_Specifications_v1.4_FINAL.txt` (BR-EL-xxx),
  `06_ELM_Workflow_Specifications_v1.6_FINAL.txt` (CW-EL-xx), `03_ELM_Use_Case_Specifications_v1.4_FINAL.txt`.

---
---

## P1 — Register the module into Django

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4 + DRF).

I have an ELM leave module at modules/leave/ that is NOT wired into Django yet.
Fix exactly these three things and nothing else:

1. config/settings/base.py — add "modules.leave" to the DOMAIN_MODULES list
   (currently only contains "modules.placement"). Keep the existing comment style.

2. modules/leave/api/urls.py — CREATE this file. First read modules/leave/api/views.py
   and list EVERY APIView class defined there (MyRequestsView, MyBalancesView,
   RequestDetailView, WithdrawView, ReplacementSubstituteView, SubstitutionInboxView,
   TaskInboxView, UnitHeadReviewView, EstablishmentRouteView, FinalDecisionView,
   ExtensionView, ResumptionView, ResumptionReviewView, CancellationView, plus any admin/
   calendar/policy views). Then write urlpatterns routing all of them, copying the exact
   style of modules/placement/api/urls.py: path("...", v.ViewName.as_view(), name="leave-...").
   Use <int:pk> for detail/action views that take pk. Module prefix for names: "leave-".
   Import views as `from modules.leave.api import views as v`.

3. config/urls.py — add one line to urlpatterns, in the same style as the placement and
   directory lines:
       path("api/v1/leave/", include("modules.leave.api.urls")),
   Do not reorder or change any other line.

Constraints: Django/DRF only — no FastAPI, no new requirements, no other files touched.
If a view needs a URL shape you cannot infer from its get/post signature, read
modules/leave/api/views.py fully first — do not invent endpoints that have no view.

Verification I will run:
    .venv/bin/python manage.py check
Paste the complete output of manage.py check. If it reports errors, fix them before finishing.
```
**Verification:** `.venv/bin/python manage.py check` → `System check identified no issues (0 silenced).`

---

## P2 — Migrations

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4).

modules/leave/ has models.py but no migrations/ directory, so its tables cannot be created.

Do this:
1. Create modules/leave/migrations/__init__.py (empty file — the directory must exist).
2. Tell me the exact command to generate migrations for this app
   (python manage.py makemigrations leave) and the command to apply them (make migrate).
3. Read modules/leave/apps.py — the AppConfig must have name="modules.leave" and
   label="leave". If label is missing, add it.

Do NOT edit models.py unless makemigrations itself reports it must change — if it does,
paste me the full makemigrations output first and wait for my reply.

Verification I will run:
    .venv/bin/python manage.py makemigrations leave
    .venv/bin/python manage.py migrate
Paste both outputs.
```
**Verification:** both commands succeed; `psql`/Django shows `leave_*` tables after migrate
(DB must be up: `make up` first if needed).

---

## P3 — Domain rule tests + fix (THE core step)

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4, pure-Python domain layer).

Task: audit modules/leave/domain/categories.py against the official business rules in
04_ELM_Business_Rule_Specifications_v1.4_FINAL.txt (plain text, read it), write tests that
encode the SPEC's expected behavior, then fix the code so the tests pass.

The three rules tied to this file that MUST pass:

- BR-EL-007: unused VL converts to EL at 2 VL : 1 EL — i.e. EL = available / 2, fractional
  results kept (Decimal division, NOT multiplication). Function: year_end_action().
- BR-EL-011: CL/SCL/RH count duty days only — BOTH Saturday and Sunday are excluded from
  the count for every date in range. Function: weekend_dates().
- BR-EL-012: two half-day CL requests on the SAME date overlap only if they occupy the
  SAME half; first-half vs second-half on the same date must return NOT overlapping.
  Function: Interval.overlaps().

Procedure (do not skip order):
1. Read modules/leave/domain/categories.py completely.
2. Create modules/leave/tests/__init__.py and modules/leave/tests/test_domain_rules.py
   with one test class per rule above, test names citing the BR number. Tests encode the
   spec text I quoted — they may fail on first run.
3. Run: .venv/bin/python -m pytest modules/leave/tests/test_domain_rules.py -v
4. For each failure: compare the failing function against the BR text, state in one line
   what the code does vs what the spec says, then apply the minimal fix to categories.py.
5. Re-run until all pass. Paste the final pytest output.

Constraints: fix ONLY what the failing tests justify; no refactors, no renames, no changes
outside modules/leave/domain/categories.py and modules/leave/tests/. Django/DRF only.
```
**Verification:** `.venv/bin/python -m pytest modules/leave/tests/test_domain_rules.py -v` → all green.

---

## P4 — Workflow/service API tests

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4 + DRF).

The leave module (modules/leave/) now has URLs mounted at /api/v1/leave/.
Write integration tests in modules/leave/tests/test_api.py. Read these first:
- modules/placement/tests/test_api.py  ← copy its fixture/auth/primitives style exactly
- modules/leave/api/views.py           ← the endpoints and required permissions
- modules/leave/registry.py            ← ROLE_GRANTS / permission names

Cover, at minimum:
1. Happy path: apply for leave → Unit Head review → Establishment route → final approve
   (use the service/API flow that exists; do not invent endpoints).
2. Authorization scoping: a user with no scope over a request gets 404 (NOT 403) from
   RequestDetailView — the selectors scope querysets, 404 not 403.
3. CW-EL-03: extension of an ongoing approved leave via ExtensionView
   (services/applications.py::request_extension).
4. CW-EL-04: resumption submit (submit_resumption) then review (decisions.py::review_resumption).
5. A permission-denied case: user without leave.request.review hitting UnitHeadReviewView
   → 403.

If a test cannot pass because of a real defect, paste me the traceback and the suspicious
code with your one-line diagnosis BEFORE changing production code.

Verification: .venv/bin/python -m pytest modules/leave/tests/ -v
Paste the final output.
```
**Verification:** `.venv/bin/python -m pytest modules/leave/tests/ -v` → all green.

---

## P5 — Registry: permissions, nav, status

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4).

modules/leave/registry.py still has MODULE["status"] = "planned" and must be finalized.
Read modules/leave/registry.py fully, plus docs/03-platform/module-authoring-guide.md
section on the registry and nav.

Do:
1. Verify every NAV_ITEMS entry has a required_permission that exists in PERMISSIONS,
   and every route in NAV_ITEMS ("to" values like /leave/mine) corresponds to a real
   frontend route OR is currently unreachable because there is no frontend yet — report
   which of the two is true; the repo has no client/src/modules/leave/ so routes exist
   only in the registry. If ops/checks/nav_matches_routes.py fails, tell me the output
   before changing anything.
2. Verify ROLE_GRANTS keys are designation names that exist (compare with how
   modules/placement/registry.py does it).
3. Only if steps 1–2 are clean: flip MODULE["status"] from "planned" to "active".
4. Run .venv/bin/python manage.py permission_manifest and paste output; then
   .venv/bin/python manage.py permission_manifest --check.

Do not touch other modules' registries.
```
**Verification:** `.venv/bin/python manage.py permission_manifest --check` exits 0.

---

## P6 — Full CI sweep + report

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4 + DRF + React).

Run-through: I will execute `make check`, which runs, in order:
  manage.py check · makemigrations --check --dry-run · ruff check . · lint-imports ·
  ops/checks/no_cross_module_fk.py · ops/checks/contracts_are_plural.py ·
  ops/checks/nav_matches_routes.py · permission_manifest --check ·
  openapi schema-check (regenerate with `make schema` if endpoints changed) · pytest -q

Tell me, for each likely failure class, the fix you expect to apply:
- ruff lint errors → show the exact ruff rule and the corrected lines
- schema-check mismatch → confirm `make schema` must be re-run after adding urls
- pytest failures → traceback + one-line root cause each
Then I will paste `make check` output and you fix ONLY the reported failures, smallest
diff possible, one failure at a time.

Finally produce my Phase-2 report skeleton:
  1. Spec violations found (BR/UC number, file:line, what was wrong, the fix)
  2. Tests added (file + count)
  3. Integration gaps closed (INSTALLED_APPS, urls, migrations, registry)
  4. What a reviewer should manually test in the running app
     (make up && make migrate && make seed && make dev → sign in → Leave in sidebar)
No claims of success I have not verified with command output.
```
**Verification:** `make check` → passes; `make check-client` only if `client/` was touched.

---

## Fallback prompt (use any time something breaks)

```
Repo: /home/atharva/Documents/Fusion/Fusion-Integrated (Django 4 + DRF).
My last step failed. Full output:

<paste the entire error/pytest/ruff output here>

Diagnose the root cause in 3 lines max, then give the minimal patch: exact file, exact
old line, exact new line. Django/DRF only; no FastAPI; touch nothing outside
modules/leave/, config/settings/base.py, config/urls.py.
```
