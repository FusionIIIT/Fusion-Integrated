---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
test-of-this-doc: >
  A developer who has never seen the repo should be able to follow this unaided and end with a
  working, granted, tested module. If they need to ask a question, this document has a gap — fix it.
---

# Module Authoring Guide

Eight steps to add a backend module. Worked example: a `complaints` module (maintenance complaints —
raise, assign, resolve).

Read [platform-structure.md](platform-structure.md) first for the layering rules, and
[shared-kernel-reference.md](shared-kernel-reference.md) before you put anything in `core/`.

```bash
make new-module NAME=complaints        # scaffolds steps 1–2; the rest is yours
```

---

## Step 0 — Decide it is a module

Before scaffolding, answer these. If any answer is uncomfortable, stop and discuss.

- **Is this one bounded context?** If the answer is "a bit of two", it is two modules. "Complaints" and
  "work orders" might be one; "complaints" and "hostel allocation" are not.
- **Does it own its data?** A module with no tables of its own is a service layer over another module, and
  belongs inside it.
- **What does it need from other modules?** Each answer is a `contracts.py` function on **their** side, and
  you must agree it with them. If the list is long, the boundary is probably wrong.
- **Will it constantly need to join to another module's tables?** That is real evidence they are one
  module. Merge them; do not add a foreign key
  ([ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)).
- **Does it need academic data?** Then it goes through `modules/academics`, never the ERP directly
  ([ADR-0007](../01-architecture/adr/0007-read-only-erp-access-via-acl.md)).

---

## Step 1 — Scaffold and register the app

```
services/platform/modules/complaints/
├── __init__.py  apps.py  contracts.py  permissions.py  registry.py
├── events.py  tasks.py  models.py  admin.py  migrations/__init__.py
├── domain/{__init__.py, entities.py, state_machine.py, errors.py}
├── selectors/{__init__.py, complaints.py}
├── services/{__init__.py, complaints.py}
├── api/{__init__.py, urls.py, filters.py, permissions.py,
│        serializers/{read.py, write.py}, views/complaints.py}
└── tests/{__init__.py, factories.py, test_domain.py, test_services.py, test_api.py}
```

```python
# apps.py
class ComplaintsConfig(AppConfig):
    name = "modules.complaints"
    label = "complaints"
    verbose_name = "Complaints"

    def ready(self) -> None:
        from . import events          # registers event handlers
        events.register()
```

Add `"modules.complaints"` to `INSTALLED_APPS`, and its layer stack to `.importlinter`. **Do this now** —
the layering contract must exist before the first import goes in the wrong direction.

---

## Step 2 — Declare permissions and the registry entry

```python
# permissions.py
MODULE_CODE = "complaints"

PERMISSIONS = [
    P("complaints.complaint.view_self",  "View own complaints"),
    P("complaints.complaint.create",     "Raise a complaint"),
    P("complaints.complaint.view",       "View complaints, within scope"),
    P("complaints.complaint.assign",     "Assign a complaint to a worker"),
    P("complaints.complaint.update",     "Record progress on a complaint"),
    P("complaints.complaint.approve",    "Mark a complaint resolved"),
    P("complaints.export.pii",           "Export complainant-identifying data", dangerous=True),
]
```

```python
# registry.py
MODULE = M(code="complaints", label="Complaints", icon="FaTools",
           base_path="/complaints", nav_section="Campus", sort_order=300,
           status="planned",            # ← planned until it is ready to be seen
           legacy_column_name="complaint_management")   # the ERP's globals_moduleaccess column

NAV_ITEMS = [
    N("complaints.mine",    "My Complaints", "FaListUl",   "/complaints/mine",
      required_permission="complaints.complaint.view_self"),
    N("complaints.queue",   "Queue",         "FaInbox",    "/complaints/queue",
      required_permission="complaints.complaint.view"),
    N("complaints.reports", "Reports",       "FaChartBar", "/complaints/reports",
      required_permission="complaints.complaint.view"),
]
```

Declaring a permission is only half of it. Say who may hold it, in the same file:

```python
# registry.py
SYSTEM_PERMISSIONS = ["complaints.complaint.auto_close"]   # only a task does this

_RESIDENT = ["complaints.complaint.view_self", "complaints.complaint.create"]
_WARDEN = [*_RESIDENT, "complaints.complaint.view", "complaints.complaint.assign"]

ROLE_GRANTS = {"student": _RESIDENT, "warden": _WARDEN}
```

Four things to get right:

- Permission codes follow `<module>.<resource>.<action>` with an action from the closed vocabulary. CI
  enforces the regex and that the first segment names a real module
  ([rbac-model.md](../02-iam/rbac-model.md#permission-codes)).
- **Every permission needs a holder in `ROLE_GRANTS`, or a place in `SYSTEM_PERMISSIONS`.** A code no
  designation holds does not fail loudly: the nav item is filtered out of the sidebar and the endpoint
  answers 403 forever. `make check` refuses it for that reason.
- `status="planned"` means nobody sees it. Flip to `active` in the last commit of the last sub-phase.
- `legacy_column_name` only if the ERP has a matching `globals_moduleaccess` column. Wrong or invented
  values fail the H2 parity check.

Then `make permissions`, which writes `registry/permissions.json` and
[permission-catalog.generated.md](../02-iam/permission-catalog.generated.md). CI fails on a stale diff.
The IAM seeds from that manifest on deploy — this module's registry is the source of truth for who holds
what, and the IAM only stores the answer.

---

## Step 3 — Model the domain first, in pure Python

**Write `domain/` before `models.py`.** Designing tables first makes the rules follow the schema; designing
rules first produces a schema that fits them.

```python
# domain/state_machine.py
class ComplaintStatus(StrEnum):
    OPEN = "open"; ASSIGNED = "assigned"; IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"; CLOSED = "closed"; REJECTED = "rejected"

TRANSITIONS: tuple[Transition, ...] = (
    Transition(ComplaintStatus.OPEN, ComplaintStatus.ASSIGNED,
               permission="complaints.complaint.assign",
               guards=(has_worker,), effects=("notify_worker",)),
    Transition(ComplaintStatus.OPEN, ComplaintStatus.REJECTED,
               permission="complaints.complaint.approve",
               guards=(has_reason,), effects=("notify_complainant",)),
    Transition(ComplaintStatus.ASSIGNED, ComplaintStatus.IN_PROGRESS,
               permission="complaints.complaint.update"),
    Transition(ComplaintStatus.IN_PROGRESS, ComplaintStatus.RESOLVED,
               permission="complaints.complaint.approve",
               guards=(has_resolution_note,), effects=("notify_complainant",)),
    Transition(ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED,
               permission="complaints.complaint.approve"),
    Transition(ComplaintStatus.RESOLVED, ComplaintStatus.IN_PROGRESS,   # reopen
               permission="complaints.complaint.update", guards=(has_reason,)),
)

TERMINAL = {ComplaintStatus.CLOSED, ComplaintStatus.REJECTED}
```

A **declarative table**, not `if` chains. An illegal transition becomes impossible to express rather than
merely rejected, and the table is directly renderable into a Mermaid diagram for the docs.

No Django import in this file. CI enforces that, and it is what makes the next step cheap.

```python
# tests/test_domain.py — fast, no database
def test_cannot_resolve_an_open_complaint():
    with pytest.raises(InvalidTransition):
        validate_transition(ComplaintStatus.OPEN, ComplaintStatus.RESOLVED, perms={"*"})

@given(st.sampled_from(list(ComplaintStatus)))
def test_terminal_states_have_no_outgoing_transitions(status):
    if status in TERMINAL:
        assert not [t for t in TRANSITIONS if t.frm == status]
```

---

## Step 4 — Models

```python
# models.py
class Complaint(TimeStampedModel):
    complainant_user_id = models.IntegerField(db_index=True)   # IAM erp_user_id — NO FK
    category   = models.ForeignKey("complaints.Category", on_delete=models.PROTECT)  # same module: fine
    location   = models.CharField(max_length=160)
    description = models.TextField(max_length=4000)
    status     = models.CharField(max_length=16, choices=ComplaintStatus.choices,
                                 default=ComplaintStatus.OPEN)
    assigned_worker_id = models.IntegerField(null=True, blank=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(status__in=ComplaintStatus.values),
                                   name="complaint_status_valid"),
            models.CheckConstraint(
                check=~Q(status="resolved") | Q(resolved_at__isnull=False),
                name="complaint_resolved_has_timestamp"),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="complaint_status_recent_idx"),
            models.Index(fields=["complainant_user_id", "-created_at"],
                         name="complaint_complainant_idx"),
            models.Index(fields=["assigned_worker_id"], condition=~Q(status__in=["closed", "rejected"]),
                         name="complaint_worker_open_idx"),
        ]

class ComplaintTransition(models.Model):        # append-only audit
    complaint  = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=16)
    to_status   = models.CharField(max_length=16)
    actor_user_id = models.IntegerField(null=True)
    reason     = models.CharField(max_length=300, blank=True)
    at         = models.DateTimeField(auto_now_add=True)
```

Points that matter:

- `complainant_user_id` is an **integer, not an FK** — it crosses a boundary
  ([ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)).
- Indexes are explicit, named, and each matches a real query's `WHERE` + `ORDER BY`. The partial index on
  open complaints per worker is the one a worker's queue page needs.
- `CheckConstraint`s encode invariants the database can enforce. The `resolved_has_timestamp` one catches
  the bug where a status is set without its timestamp.
- No business logic. No `save()` override — `bulk_update` and `queryset.update()` bypass it anyway.

```bash
python manage.py makemigrations complaints
python manage.py migrate
```

Then add the table to `ops/db/roles.sql`. CI fails if a table has no explicit grant, so a new table cannot
silently inherit broad access.

---

## Step 5 — Selectors and services

```python
# selectors/complaints.py
def visible_complaints(principal) -> QuerySet[Complaint]:
    """Ownership and scope live HERE — once per module, not once per view."""
    qs = Complaint.objects.select_related("category")
    if principal.has_perm("complaints.complaint.view"):
        scope = principal.active_assignment.scope
        if scope and scope.type == "department":
            return qs.filter(complainant_user_id__in=directory.user_ids_in_department(scope.id))
        return qs
    return qs.filter(complainant_user_id=principal.erp_user_id)
```

```python
# services/complaints.py
def transition(*, complaint_id: int, to_status: str, principal, reason: str = "") -> Complaint:
    with transaction.atomic():
        c = Complaint.objects.select_for_update().get(pk=complaint_id)
        validate_transition(c.status, to_status, principal.permissions, reason=reason)  # domain
        frm, c.status = c.status, to_status
        if to_status == ComplaintStatus.RESOLVED:
            c.resolved_at = timezone.now()
        c.save(update_fields=["status", "resolved_at", "updated_at"])
        ComplaintTransition.objects.create(complaint=c, from_status=frm, to_status=to_status,
                                           actor_user_id=principal.erp_user_id, reason=reason)
        emit("complaints.complaint.status_changed",
             {"complaint_id": c.id, "from": frm, "to": to_status,
              "complainant_user_id": c.complainant_user_id, "actor_user_id": principal.erp_user_id},
             dedupe_key=f"complaint.status:{c.id}:{frm}->{to_status}:{c.updated_at.timestamp()}")
    return c
```

Note: `select_for_update` (two coordinators must not transition the same complaint concurrently), the domain
call for validation, an append-only audit row, and `emit()` **inside** the transaction — the outbox pattern
([ADR-0006](../01-architecture/adr/0006-outbox-plus-celery-for-integration-events.md)).

The service raises a **domain** error, never a DRF one.

---

## Step 6 — API

```python
# api/views/complaints.py
class ComplaintListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("complaints"),
                          HasAnyPermission("complaints.complaint.view",
                                           "complaints.complaint.view_self")]
    filterset_class = ComplaintFilter

    def get_queryset(self):
        return selectors.visible_complaints(self.request.principal)   # never Complaint.objects

    def get_serializer_class(self):
        return WriteComplaintSerializer if self.request.method == "POST" else ReadComplaintSerializer

    @extend_schema(summary="List complaints visible to the caller", tags=["complaints"],
                   examples=[OpenApiExample("open complaint", value={...})])
    def get(self, *a, **kw):
        return super().get(*a, **kw)
```

Checklist per endpoint is in
[api-conventions.md](../01-architecture/api-conventions.md#10-checklist-for-a-new-endpoint). The
`@extend_schema` example is not optional — it becomes the MSW mock in frontend tests, which is what stops
frontend mocks drifting from the API.

```bash
python manage.py spectacular --file openapi/platform.v1.yaml --validate --fail-on-warn
```

Commit the schema. CI runs `git diff --exit-code openapi/`.

---

## Step 7 — `contracts.py` and events

```python
# contracts.py — the ONLY thing other modules may import
def get_complaint_counts(user_ids: Sequence[int]) -> dict[int, ComplaintCountsDTO]:
    """Open/resolved counts per user. Plural by signature — an N+1 is unwritable."""
    rows = (Complaint.objects.filter(complainant_user_id__in=user_ids)
            .values("complainant_user_id").annotate(
                open=Count("pk", filter=~Q(status__in=TERMINAL)),
                resolved=Count("pk", filter=Q(status="resolved"))))
    return {r["complainant_user_id"]: ComplaintCountsDTO(**r) for r in rows}
```

```python
# events.py
PRODUCES = ("complaints.complaint.created", "complaints.complaint.status_changed")

def register() -> None:
    subscribe("iam.user.status_changed", on_user_status_changed)   # reassign open complaints

def on_user_status_changed(event: IamUserStatusChanged) -> None:
    if event.to_status in ("suspended", "archived"):
        flag_open_complaints_for_review(event.user_id)     # flag — never auto-close
```

Add both topics to [event-catalog.md](../01-architecture/event-catalog.md), with pydantic models in
`packages/fusion_contracts`. A topic in code but not in the catalog fails CI.

`contracts.py` **never mutates.** If another module needs a change here, that is an event.

---

## Step 8 — Frontend, grant, activate

1. Frontend module — see
   [module-authoring-guide-frontend.md](../05-frontend/module-authoring-guide-frontend.md). `manifest.code`
   **must** equal `registry_module.code`; a CI check asserts the two sets match.
2. Grant the module to roles: `registry_role_module_grant` rows via a data migration or the shell.
3. Flip `registry_module.status` to `active` in the final commit.

Until step 3, the module is invisible **and unroutable** — the frontend produces no route for an ungranted
module. That is what makes shipping a half-finished module safe in production.

---

## Definition of done

- [ ] `domain/` has no Django import; `test_domain.py` at 90%
- [ ] Every read through a selector; every write through a service
- [ ] Ownership/scope filtering in the selector, so a foreign id yields **404**
- [ ] No cross-module FK (CI); no other module's internals imported (CI)
- [ ] Explicit named indexes matching real query shapes; `CheckConstraint`s for invariants
- [ ] Tables added to `ops/db/roles.sql`
- [ ] `makemigrations --check` clean; `django-migration-linter` clean
- [ ] OpenAPI committed and diff-clean; every endpoint has a schema example
- [ ] Permissions seeded; catalog regenerated and diff-clean
- [ ] Events in the catalog with pydantic models; a replay test per consumer
- [ ] `django_assert_max_num_queries` budget per list endpoint; `nplusone` clean
- [ ] Error paths tested: 401, 403/404, 409, 422, 429
- [ ] Frontend manifest matches `registry_module.code`
- [ ] `status = "active"` only in the final commit

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| FK to another module's model | CI fails | plain `user_id`, read via `contracts` |
| Singular `get_x(id)` in `contracts.py` | CI fails; N+1 in review | make it plural |
| Business logic in `models.py` | untestable without a database; bypassed by `bulk_update` | move to `domain/` + `services/` |
| `Complaint.objects` in a view | ownership filter missing on some path | go through the selector |
| DRF exception from a service | unusable from a task or command | raise a domain error; map in `core/api/exceptions.py` |
| `db_index=True` sprinkled | wrong index, right column | `Meta.indexes`, composite, matching the real query |
| Forgot `emit()` inside the transaction | events fire for rolled-back writes | `emit()` before the `atomic` block closes |
| `status="active"` too early | a half-built module is visible in production | `planned` until the end |
| Reading `Student.cpi` | it is permanently `0.0` — CI greps for this | `academics.contracts.get_standings()` |
