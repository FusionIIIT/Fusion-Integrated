---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
note: >
  Every claim here was verified by reading the code at the cited path:line on 2026-08-01.
  Citations are relative to /Users/vikrant/Documents/Fusion/. If you find a stale citation,
  that is a bug in this document — fix it.
---

# Current-State Assessment

An honest inventory of what exists before we add to it. This document exists so nobody has to
rediscover any of it, and so the design decisions in
[vision-and-scope.md](vision-and-scope.md) can be traced to evidence.

---

## 1. The estate

Three independent git repositories:

| Repo | What it is | Branch | Size |
|---|---|---|---|
| `Fusion/` | The main Django monolith, at `Fusion/FusionIIIT/` | `prod/acad-react` | ~106.6k LOC Python excl. migrations (115.7k incl.); **1,167 Django templates / ~198.9k lines** |
| `Fusion-client/` | React SPA for the academic modules | `acad-main` | ~73.7k LOC JS/JSX |
| `Fusion_System_Administrator/` | A separate Django 5.1 + DRF admin console with its own React client, deployed at `/sysadmin/` | `main` | 6.1k LOC Python + 9.6k LOC JS |

There is **no `docs/`, no `ARCHITECTURE.md` and no onboarding guide** anywhere in any of the
three. This documentation set is the first.

Production branches (per `Fusion/README.md`): backend `prod/acad-react`, frontend `acad-main`.

---

## 2. The monolith: what is actually live

`Fusion/FusionIIIT/applications/` contains **34 Django apps** and roughly **424 concrete models**.
Only a handful are real.

The authoritative signal is in the repo itself —
`Fusion/FusionIIIT/security_check.py:26-29`, a homegrown endpoint-auth regression guard:

```python
"""Endpoint-auth regression guard for the in-production Fusion apps."""
APPS = [
    "academic_information", "academic_procedures",
    "examination", "online_cms", "programme_curriculum",
]
```

Six months of git churn corroborates it: `examination` 39 commits · `academic_procedures` 15 ·
`academic_information` 15 · `globals` 11 · `programme_curriculum` 10 · **everything else ≤ 1**.

### Live (do not break)

| App | LOC | Role |
|---|---|---|
| `programme_curriculum` | 14,394 | Programmes, disciplines, curricula, batches, courses. Largest app. |
| `academic_procedures` | 11,968 | Registration, branch change, thesis, fees, dues, bonafide |
| `examination` | 5,196 | Grades, results, transcripts. **API-only** — no `views.py` at all; 5,079 LOC live in `api/`. |
| `academic_information` | 4,805 | Student, Course, Curriculum, attendance, calendar |
| `online_cms` | 3,241 | LMS. Also holds `Student_grades`, which is the real grade store. |
| `globals` | 3,422 | **Identity and RBAC.** Everything depends on it. |
| `eis` | 3,734 | Faculty professional profile / research output |

### Deprecated (26 apps, ~60k LOC, ~290 models)

`establishment` (19 models) · `hr2` (12) · `leave` (14) · `finance_accounts` (5) ·
`income_expenditure` (7) · `ps1` (4) · `office_module` (32) · `hostel_management` (18) ·
`central_mess` (19) · `health_center` (15) · `complaint_system` (5) · `gymkhana` (16) ·
`visitor_hostel` (7) · `placement_cell` (25) · `library` (**0 models** — it scrapes the institute
WebOPAC with BeautifulSoup) · `iwdModuleV2` (22) · `estate_module` (5) · `scholarships` (10) ·
`research_procedures` (7) · `filetracking` (2) · `notifications_extension` (0) · `department` (3) ·
`counselling_cell` (9) · `recruitment` (24, near-empty views) · `feeds` (11) · `otheracademic` (7).

**14 of these have no DRF `api/` layer at all** and are still pure Django templates:
`establishment`, `estate_module`, `finance_accounts`, `income_expenditure`, `hostel_management`,
`iwdModuleV2`, `library`, `office_module`, `otheracademic`, `recruitment`, `scholarships`,
`visitor_hostel`, `feeds`, `counselling_cell`.

Roughly **56% of the backend Python and 68% of the models are non-academic** — and effectively none
of it is in service.

### The concrete case for not porting

`applications/placement_cell/views.py:3693` filters candidate students with `cpi__gte=...` against
`academic_information.Student.cpi`. That column is **permanently `0.0`**: its only writers set it to
zero at student creation (`programme_curriculum/signals.py:117`,
`programme_curriculum/api/views_student_management.py:5013`,
`academic_information/views.py:1388`). `academic_information.Spi` has **zero writers** at all.
`gymkhana/views.py:749,911` reads the same dead column.

The old placement module has been filtering on zero for its entire existence. This is what "the
non-academic code is deprecated" means in practice, and it is why
[NG2](vision-and-scope.md#non-goals) is a non-goal rather than a nice-to-have.

---

## 3. Authentication as it stands

**No custom user model.** `AUTH_USER_MODEL` is never set, so it is stock
`django.contrib.auth.models.User` (`auth_user`), extended by a `OneToOneField` from
`globals.ExtraInfo` (whose primary key is a `CharField`, matching `User.username`).

**No JWT**, despite `PyJWT==2.6.0` sitting in `requirements.txt` — there is no `import jwt` anywhere.
Auth is:

- **DRF `authtoken`** for the SPA — a single opaque key per user, **rotated on every login**
  (`globals/api/serializers.py:17-32`, where the token is minted inside a serializer field, which is
  a surprising place for a side effect).
- Expiry does not exist in DRF, so `globals/api/token_auth_patch.py` **monkey-patches**
  `TokenAuthentication.authenticate_credentials` at import time (triggered from
  `globals/api/urls.py:6`) to enforce `TOKEN_MAX_AGE_SECONDS = 8 * 60 * 60`.
- **Django sessions + allauth** for the remaining server-rendered pages. Google OAuth is configured
  in settings but `allauth.socialaccount.providers.google` is commented out of `INSTALLED_APPS`.

Endpoints (all at the root, because `globals.urls` is mounted at `r'^'`): `POST /api/auth/login/`,
`POST /api/auth/logout/`, `GET /api/auth/me`, `PATCH /api/update-role/`, plus a bespoke three-step
OTP password reset (HMAC-SHA256 OTP hash, 10-min TTL, 5 attempts, 3/hour, then a single-use SHA-256
reset token with a 15-min TTL — this part is well built).

**Client side.** `Fusion-client` hardcodes `host = "http://127.0.0.1:8000"` in
`src/routes/globalRoutes/index.jsx`. The token is stored in **both** `sessionStorage` and
`localStorage`, and `App.jsx:39-116` runs a `BroadcastChannel("fusion-auth-session")` handshake to
decide whether a `localStorage` token survived a browser restart. There is **no shared axios
instance and no interceptors** — every call site reads storage and builds its own
`Authorization: Token …` header. Idle logout is 5 minutes.

---

## 4. Authorization as it stands

### The models — `applications/globals/models.py`

```python
class Designation(models.Model):                      # line 74
    name      = models.CharField(max_length=50, unique=True, default='student')
    full_name = models.CharField(max_length=100, default='...')
    type      = models.CharField(max_length=30, default='academic',
                                 choices=Constants.DESIGNATIONS)

class HoldsDesignation(models.Model):                 # line 166
    user        = models.ForeignKey(User, related_name='holds_designations', ...)
    working     = models.ForeignKey(User, related_name='current_designation', ...)
    designation = models.ForeignKey(Designation, related_name='designees', ...)
    held_at     = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = [['user', 'designation'], ['working', 'designation']]
```

The docstring says: *"'working' always refers to the user who's holding the title… **Use 'working' to
handle permissions in code**."*

```python
class ModuleAccess(models.Model):                     # line 318
    designation            = models.CharField(max_length=155)   # free text, NOT a FK
    program_and_curriculum = models.BooleanField(default=False)
    course_registration    = models.BooleanField(default=False)
    examinations           = models.BooleanField(default=False)
    ... 20 boolean columns in all ...
```

### Four problems

**P1 — `unique_together ('working', 'designation')` means only one person institute-wide may hold a
designation.** Two placement coordinators cannot both be recorded. This is hazard **H1** and it is the
single biggest obstacle to projecting a modern role model back into the ERP.

**P2 — module access is a column-per-module keyed by free text.** Adding a module is a schema
migration. Renaming a designation silently orphans its access row. `ExtraInfo.last_selected_role` is
`max_length=20` while `Designation.name` is 50 and `ModuleAccess.designation` is 155, so long role
names cannot round-trip through `PATCH /api/update-role/` (hazard **H3**).

**P3 — `ModuleAccess` gates menus only.** `GET /api/auth/me` (`globals/api/views.py:79-114`) builds
`accessible_modules` as `{designation: {module: bool}}`; `Fusion-client/src/components/sidebarContent.jsx:195-200`
filters a static `Modules` array against it, where each entry's `id` **must exactly match a
`ModuleAccess` column name**. There is **no middleware and no permission class anywhere that maps a
request URL to a module flag.** A user who knows an endpoint URL is stopped only if that specific view
happens to carry a check.

**P4 — three parallel, disagreeing enforcement mechanisms:**

| Mechanism | Where | Queries |
|---|---|---|
| `access.py` — the newest, fail-closed layer: `user_holds_role`, `user_holds_any_role`, `HasDesignation`, `has_any_role(*roles)`, `require_designation(*roles)` | `applications/globals/access.py` | `Q(working=user) \| Q(user=user)` |
| `role_required(allowed_roles)` — older, used ~18× in `academic_information` alone | `applications/academic_procedures/api/views.py:119` | **`user=` only** — contradicts the model docstring |
| `/api/auth/me` and `user_logged_in_middleware` | `globals/api/views.py`, `Fusion/middleware/custom_middleware.py` | **`working=` only** |

Plus a fourth path: `examination/api/views.py` contains a local duplicate `_user_has_exam_admin_role`
(line 3336) whose docstring is candid about why — *"The rest of this module trusts a client-supplied
`Role` field, which is spoofable; these result-publishing endpoints verify the real designation
instead."* The vestigial `Role` / `role` request parameters are read into local variables across the
module and then never used.

`applications/globals/access.py` is genuinely good code and its shape (fail-closed permission classes
plus a factory) is what the new `HasPermission` is modelled on.

### Middleware hazards

`Fusion/middleware/custom_middleware.py` runs on every authenticated request, re-queries
designations and stuffs them into the session. Two latent crashes: `designation[0]` raises
`IndexError` for a non-student with zero `HoldsDesignation` rows, and `access_rights` is referenced
outside its `if module_access:` guard (`UnboundLocalError` when no `ModuleAccess` row matches). It
also registers a `@receiver(user_logged_in)` on *every* request.

`helpers/decorators.py` contains `critical_section` (broken — `@wraps` used bare) and
`designation_filter` (a `pass` stub).

---

## 5. Databases

**The monolith has one database alias and no router.** `Fusion/settings/development.py:9-17` and
`production.py:14-22` are **identical**, both hardcoding `NAME = 'fusionlab'`, the user, and the
password — with no `PORT` and no env-var indirection.

Production actually runs **`fusion_newui_prod`** (per
`Fusion_System_Administrator/README.md:16` and `DEPLOYMENT.md:25-26`), so `production.py` names the
wrong database. It works only because whatever deploys it overrides the value out of band.

The admin console does this correctly — `django-environ`, two aliases, a router:

```python
DATABASES = {
    "default":   {... "NAME": env("DB_NAME", default="fusionlab") ...},          # the ERP
    "system_db": {... "NAME": env("SYSTEM_DB_NAME", default="fusion_system_db")},
}
DATABASE_ROUTERS = ["backend.routers.SystemDBRouter"]
```

`SystemDBRouter` sends `{django_apscheduler, auth, admin, sessions, contenttypes, authtoken}` and
`{backuprecord, restorerecord, backupschedule, healthcheck, archivelog}` to `system_db`, and its
`allow_migrate` is strictly exclusive. Its docstring explains the consequence plainly: *"This is what
makes admin operators a separate account set from the 3277 managed ERP users."*

So there are **two token systems and two user pools**: the monolith issues 8-hour DRF tokens against
`auth_user` in the ERP database; the console issues 12-hour cookie tokens against `auth_user` in
`fusion_system_db`. Neither can authenticate the other's users.

### Schema drift

`Fusion_System_Administrator/Backend/backend/api/views/schema.py:12-52` applies **raw `ALTER TABLE`**
statements to the ERP database. As a result, production has columns that no Django migration in the
monolith knows about:

- `globals_designation.basic`, `.category`, `.dept_if_not_basic_id`
- `globals_moduleaccess.inventory_management`

`applications/globals/migrations/` stops at `0006_auto_20260304_0836`. **`manage.py makemigrations` on
the monolith would generate migrations that drop these columns.** The legacy `ModuleAccess` model has
20 boolean fields; the console's shadow model has 21 (it has `inventory_management` and lacks
`database`). They disagree with each other and with production. This is hazard **H2**.

---

## 6. Scale and infrastructure debt

Verified in `Fusion/FusionIIIT/Fusion/settings/`:

| Finding | Detail |
|---|---|
| **No cache at all** | There is no `CACHES` setting. Two views import `django.core.cache` (`placement_cell/views.py:17`, `academic_information/api/views.py:34`) and therefore hit Django's default **local-memory** cache — per-process, not shared across gunicorn workers, so it is worse than useless for correctness. |
| **Celery cannot boot** | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are **commented out** (`common.py:82-83`), and `Fusion/celery.py` sets `DJANGO_SETTINGS_MODULE = 'Fusion.settings'` — a module that does not exist (it is `Fusion.settings.development`). `globals/tasks.py` is an empty file. |
| Real scheduler is `django-crontab` | One job, and `CRONTAB_DJANGO_MANAGE_PATH` is hardcoded to `/home/owlman/Desktop/Fuse/...` — someone's laptop — and only in `development.py`. |
| **One index** | Exactly **one** `db_index=True` across 424 models. `Meta.indexes` appears twice, both in `programme_curriculum`. ~20 `unique_together`. |
| **A DB write per request** | `SESSION_COOKIE_AGE = 15*60` with `SESSION_SAVE_EVERY_REQUEST = True` on database-backed sessions. Combined with the designation-recomputing middleware, every authenticated request costs several queries plus a write. |
| No connection reuse | No `CONN_MAX_AGE`, so a fresh Postgres connection per request. |
| No websockets | `Fusion/routing.py` is 100% commented out; no `channels`, no `ASGI_APPLICATION`, no `asgi.py`. |
| Media through Django | `static(settings.MEDIA_URL, ...)` appended to `urlpatterns`. |
| No replicas, no pooling, no load balancing | Single alias, no router, no PgBouncer. |
| Migrations | 111 files / ~9,064 LOC across 32 apps, very lopsided (`programme_curriculum` 32, `academic_procedures` 21); **19 apps have a single `0001_initial`**. `library` has no migrations directory. |

### Security debt (all verified)

| Finding | Location |
|---|---|
| **`DEBUG = True` in production settings** | `Fusion/settings/production.py:3` |
| Hardcoded `SECRET_KEY` | `development.py:5` |
| Hardcoded DB password | `development.py`, `production.py`, `docker-compose.yml`, and `README.md:272` |
| Hardcoded Google OAuth client id + secret | `common.py:23-24` |
| `CORS_ORIGIN_ALLOW_ALL = True` | `common.py:285` |
| `ALLOWED_HOSTS = ['*']` in dev | `development.py` |

`DEBUG = True` in production is the one that gates our design: any unhandled 500 renders a full
traceback page including `request.META`, which would contain an auth cookie. **It must be fixed
before IAM issues a `Path=/` cookie.** That is why it is a Phase 0 prerequisite and not a cleanup
item.

---

## 7. Testing and CI

**Effectively zero backend test coverage.**

- All 31 `applications/*/tests.py` files are the three-line Django stub. 218 lines total.
- Two exceptions: `applications/hr2/test.py` (116 lines — note `test.py`, so `manage.py test` does
  **not** discover it) and `applications/research_procedures/tests.py` (14 lines).
- No `pytest.ini`, `conftest.py`, `tox.ini`, `.coveragerc`; no `pytest`, `pytest-django`,
  `factory-boy` or `coverage` in `requirements.txt`.
- The only real test suite in the estate is
  `Fusion_System_Administrator/Backend/backend/api/tests/test_backup_restore.py` (275 lines).
- What `README.md` calls the "Testing Procedure" is a stale Java/Selenium/Cucumber project under
  `Fusion/Test/`, requiring a hardcoded chromedriver path edit, with checked-in TestNG HTML reports.
- Frontend: ESLint (airbnb) + Prettier + Husky in `Fusion-client`, but **no test runner at all**.

**CI is a welcome-bot.** `.github/workflows/` contains only
`welcome-new-contributors.yml`. No lint, test, build, migration-check or deploy workflow anywhere.
`security_check.py` describes itself as *"suitable for CI / pre-commit"* but is not wired to
anything.

This is the reason Phase 0 writes a characterization test suite for the auth contract, and the reason
Phase 2's gate is an empty-diff report rather than a code review: **there is no existing safety net
to lean on.**

---

## 8. Deployment

There is **no nginx config, no gunicorn config and no systemd unit in the monolith repo.**
`gunicorn` is in fact **commented out** of `requirements.txt`, and `docker-entrypoint.sh` runs
`manage.py runserver` — the Django development server.

`Fusion/scripts/` (`clone.sh`, `sync.sh`, `db_exec.sh`, `script.go`) spins up one docker-compose stack
per team branch on a fixed port map. That is **development fan-out, not deployment**.

The only documented production topology lives in the sibling repo,
`Fusion_System_Administrator/DEPLOYMENT.md`:

```
https://fusion.iiitdmj.ac.in/sysadmin/      -> client/dist          (nginx static)
https://fusion.iiitdmj.ac.in/sysadmin/api/  -> 127.0.0.1:8001       (gunicorn, systemd)
https://fusion.iiitdmj.ac.in/               -> the main monolith

fusion_newui_prod   ERP tables (shared with main Fusion)
fusion_system_db    the console's own tables
```

Its `fusion-sysadmin.service` unit and nginx block are the **proven pattern** the new services
extend — see [deployment-topology.md](../07-ops/deployment-topology.md).

---

## 9. `Fusion_System_Administrator` — the good one

Worth calling out separately, because the plan leans on it heavily. It does most things right:

- **httpOnly cookie auth** (`CookieTokenAuthentication`), 12-hour TTL, login throttled 5/min via
  `ScopedRateThrottle`. No token in JavaScript at all.
- **Centralized permissions** — `api/permissions.py` is nine lines and says exactly what it means:
  `ReadOnly = [IsAuthenticated]`, `Privileged = [IsAdminUser]`.
- **Config via `django-environ`**, `SECRET_KEY` required with no fallback. No committed secrets.
- **A real axios instance with a 401 interceptor**, and only a non-secret `isAuthenticated` hint in
  `localStorage`.
- 30-minute idle timeout, cross-tab logout via the `storage` event.
- A componentized login page (`pages/Login/{components,hooks,constants}`) — the opposite of
  `Fusion-client`'s 1,709-line `login.jsx`.
- `FORCE_SCRIPT_NAME` from `APP_BASE_PATH`, so it deploys under a sub-path cleanly.
- The estate's only real test suite.

Its React client is also the **design reference**: `client/src/theme.js`,
`client/src/components/AppLayout/` (66px header, 280px dark navbar
`linear-gradient(180deg,#0c1526,#080d18)`, `#15abff` accent, live sidebar search, single-level
accordion), `PageHeader`, and the `pages/UpcomingBatches/` feature layout
(`page → components/ + hooks/ + config/ + utils/`), which is the pattern new modules follow.

Two things it does **not** do, both intentional given its scope, both of which the new design must:
its sidebar is static and unfiltered (authorization is entirely server-side), and its operators are a
separate account pool.

### Known issues in it

- The 401 interceptor's `window.location.assign("/login")` is base-path-unaware — under
  `base: "/sysadmin/"` it redirects out of the app. `RequireAuth` also redirects to `"/login/"`
  (trailing slash) while the route is declared `"/login"`.
- `api/views/schema.py` applies raw DDL to the ERP database — the source of hazard **H2**.
- Dead code: three `ArchivingPages` components are unrouted; `src/data/*.js` mocks,
  `firebaseConfig.jsx`, `charts/` and the `Stats*` components are imported by no page.

---

## 10. Consequences for the design

| Finding | What it forces |
|---|---|
| `Student.cpi` is permanently `0.0`; CPI is recomputed per request with subtle S/X/F semantics | Placement **must** snapshot the ERP's own computation, never recompute. → [NG5](vision-and-scope.md#non-goals), [ADR-0008](../01-architecture/adr/0008-declared-academic-snapshot-for-cpi.md) |
| `unique_together ('working','designation')` | The projection cannot represent multi-holder or scoped roles. Needs an explicit decision before Phase 4. → hazard **H1** |
| Raw DDL drift in `globals_*` | The projector must write through an `information_schema`-derived shadow model, with a CI column check. → hazard **H2** |
| 424 models FK to `auth_user` | `auth_user` stays in the ERP database; IAM references it logically. → [ADR-0002](../01-architecture/adr/0002-separate-iam-service-and-database.md) |
| `production.py` has `DEBUG = True` | Must be fixed **before** any `Path=/` cookie is issued. Phase 0 prerequisite. |
| No tests, no CI | Phase 0 writes a characterization suite; Phase 2's gate is a 7-day empty diff, not a review. |
| No cache, broken Celery, one index | These are Phase 0 legacy-hardening items — independently valuable, and prerequisites for the new services to share Redis. |
| `ModuleAccess` gates menus only | The new platform enforces module + permission **server-side on every request**; client checks are UX only. |
| Console operators are a separate pool | IAM unifies them; the console becomes the `sysops` module in the shell (Phase 7). |
| The console's design system is good | Extract it **verbatim** into `packages/ui`, and prove it with Playwright visual baselines. |
