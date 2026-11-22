# Visitor Management System (VMS) — Architecture Blueprint

> **Module:** Visitor Management System (`vms`)  
> **Docs Folder:** `docs/09-vms/`  
> **Environment:** `module-only`  
> **Governing Specifications:**  
> - `01_VMS_Problem_Statement_v1.2_SYNCHRONIZED.docx`  
> - `02_VMS_Requirement_Registry_CFR_AFR_v1.3_FINAL.xlsx` (33 CFRs, 225 AFRs)  
> - `03_VMS_Use_Case_Specifications_v1.3_FINAL.docx` (39 Active UCs, 4 Event UCs)  
> - `04_VMS_Business_Rule_Specifications_v1.3_FINAL.docx`  
> - `05_VMS_Workflow_Specifications_v1.3_FINAL.docx` (7 Basis Workflows: BW-VMS-01 to BW-VMS-07)  
> **Author:** Student 1 (Builder — Yash Rahul Kondane, `24BCS274` / Claude Sonnet 4.6)  
> **Approver:** Student 2 (Reviewer — Vankayalapati Yaswanth, `24BCS262` / Google Flash 3.8)

---

## 1. Traceability Table

| Specification ID | Requirement / Rule Title | Architecture Layer | Enforcement Point | Architectural Notes |
| :--- | :--- | :--- | :--- | :--- |
| **VMS-CFR-001 / AFR-002** | Authoritative visitor digital lifecycle | `domain/` & `models/` | DB schema & lifecycle constraints | Single source of truth for visit requests, passes, and sessions. |
| **VMS-CFR-002 / AFR-003** | Operational role assignment & scope | `registry.py` & `selectors/` | IAM `ROLE_GRANTS` + scoping | Guards role hierarchy (Admin, Host, Security Guard). |
| **VMS-CFR-003 / AFR-004** | Identity & external service boundaries | `contracts.py` & adapters | Identity projection via `directory` | Plain integer `user_id`; no foreign keys to ERP tables. |
| **VMS-CFR-004 / AFR-005** | VIP visit override handling | `services/` | `VipVisitService` | VIP fast-track without bypassing audit logging. |
| **VMS-CFR-005 / AFR-006** | Complete operational audit logging | `domain/` & `services/` | `VisitAuditLog` model | Immutable audit entries on check-in, check-out, decision. |
| **VMS-AFR-010-01** | Pre-registration submission | `services/` | `pre_register_visitor()` | Validates mandatory fields and visit purpose. |
| **VMS-AFR-010-02** | Blacklist screening on submission | `services/` | `validate_against_blacklist()` | Rejects blacklisted phone/government ID immediately. |
| **VMS-AFR-013-01** | Host decision & pass generation | `services/` | `decide_visit_request()` | Generates active `VisitorPass` upon host `APPROVE`. |
| **VMS-AFR-018-01** | Security gate credential scan & check-in | `services/` | `check_in_visitor()` | Validates active pass, time window, and permitted zone. |
| **VMS-AFR-021-01** | Gate departure checkout | `services/` | `check_out_visitor()` | Terminates visit session, logs departure timestamp. |
| **VMS-UC-010** | Pre-register visit (Visitor Actor) | `api/` & `services/` | `/api/v1/vms/requests/` | Self-service pre-registration portal. |
| **VMS-UC-013** | Review visit request (Host Actor) | `api/` & `services/` | `/api/v1/vms/requests/{id}/decision/` | Host approval/rejection interface. |
| **VMS-UC-018** | Validate visitor pass (Guard Actor) | `api/` & `services/` | `/api/v1/vms/passes/validate/` | Gate officer QR/pass credential scanning. |
| **VMS-UC-021** | Check out visitor (Guard Actor) | `api/` & `services/` | `/api/v1/vms/sessions/{id}/checkout/` | Records physical campus departure. |
| **VMS-BR-037** | Mandatory field completeness | `serializers/` | `VisitRequestCreateSerializer` | Enforces non-blank visitor name, phone, purpose. |
| **VMS-BR-038** | Duplicate visit request prevention | `models/` & `services/` | `UniqueConstraint` on active window | Prevents simultaneous overlapping active requests. |
| **VMS-BR-051** | Blacklist registration rejection | `domain/` & `services/` | `BlacklistRegistry` check | Blocks matched phone or ID document numbers. |
| **VMS-BR-077** | Non-active pass credential denied | `services/` | `validate_visitor_pass()` | Rejects expired, deactivated, or used credentials. |
| **VMS-BR-105** | Departure logging & timestamp capture | `services/` | `check_out_visitor()` | Immutable check-out timestamp recorded. |
| **VMS-BR-190** | Temporal interval consistency | `models/` | DB `CheckConstraint` | Enforces `scheduled_start_time < scheduled_end_time`. |
| **VMS-BR-191** | Gate zone location authorization | `services/` | `validate_gate_access()` | Ensures gate belongs to `permitted_zones`. |
| **BW-VMS-01** | Pre-registered Approved Visit Lifecycle | `domain/` & `services/` | STT R1–R4 State Engine | Sequential: SUBMITTED → APPROVED → ACTIVE → COMPLETED. |

---

## 2. Domain Model & Invariants

### 2.1 Core Entities

1. **`VisitRequest`** (`UserScopedModel`, `AuditModel`)
   - `id`: AutoField (PK)
   - `visitor_name`: CharField(max_length=150)
   - `visitor_phone`: CharField(max_length=20)
   - `visitor_email`: EmailField(blank=True, null=True)
   - `id_document_type`: CharField(choices: AADHAAR, PAN, PASSPORT, VOTER_ID, DRIVING_LICENSE)
   - `id_document_number`: CharField(max_length=50)
   - `host_user_id`: IntegerField(db_index=True) — Plain integer reference to Fusion IAM
   - `purpose`: CharField(max_length=255)
   - `scheduled_start_time`: DateTimeField()
   - `scheduled_end_time`: DateTimeField()
   - `permitted_zones`: JSONField(default=list)
   - `status`: CharField(choices: SUBMITTED, APPROVED, REJECTED, EXPIRED, CANCELLED)
   - `rejection_reason`: TextField(blank=True, null=True)

2. **`VisitorPass`** (`AuditModel`)
   - `id`: AutoField (PK)
   - `request`: ForeignKey(`VisitRequest`, on_delete=CASCADE, related_name='passes')
   - `pass_number`: CharField(max_length=64, unique=True, db_index=True)
   - `qr_credential_hash`: CharField(max_length=128, unique=True)
   - `valid_from`: DateTimeField()
   - `valid_to`: DateTimeField()
   - `status`: CharField(choices: ACTIVE, EXPIRED, DEACTIVATED, COMPLETED)
   - `is_vip`: BooleanField(default=False)

3. **`VisitSession`** (`AuditModel`)
   - `id`: AutoField (PK)
   - `pass`: ForeignKey(`VisitorPass`, on_delete=PROTECT, related_name='sessions')
   - `check_in_time`: DateTimeField()
   - `check_in_gate`: CharField(max_length=50)
   - `check_in_guard_user_id`: IntegerField()
   - `check_out_time`: DateTimeField(blank=True, null=True)
   - `check_out_gate`: CharField(max_length=50, blank=True, null=True)
   - `check_out_guard_user_id`: IntegerField(blank=True, null=True)
   - `status`: CharField(choices: ACTIVE, COMPLETED, OVERSTAYED)

4. **`BlacklistRegistry`** (`AuditModel`)
   - `id`: AutoField (PK)
   - `phone`: CharField(max_length=20, blank=True, null=True, db_index=True)
   - `id_document_number`: CharField(max_length=50, blank=True, null=True, db_index=True)
   - `reason`: TextField()
   - `added_by_user_id`: IntegerField()
   - `is_active`: BooleanField(default=True)

### 2.2 Database Constraints
```python
# In models.py VisitRequest:
constraints = [
    CheckConstraint(
        check=Q(scheduled_start_time__lt=F('scheduled_end_time')),
        name="vms_request_start_before_end"
    )
]

# In models.py VisitorPass:
constraints = [
    CheckConstraint(
        check=Q(valid_from__lt=F('valid_to')),
        name="vms_pass_valid_from_before_valid_to"
    )
]
```

---

## 3. Declarative State Machine

### 3.1 VisitRequest State Machine
| Current State | Event | Trigger Actor | Next State | Guard Condition |
| :--- | :--- | :--- | :--- | :--- |
| `[INIT]` | `SUBMIT` | Visitor / Host | `SUBMITTED` | Valid schema, not blacklisted |
| `SUBMITTED` | `APPROVE` | Host Faculty/Staff | `APPROVED` | Actor is assigned host, within SLA |
| `SUBMITTED` | `REJECT` | Host Faculty/Staff | `REJECTED` | Actor is assigned host, reason provided |
| `SUBMITTED` | `TIMEOUT` | System (Celery) | `EXPIRED` | Current time > request validity start |
| `APPROVED` | `CANCEL` | Host / Admin | `CANCELLED` | Pass not yet checked in |

### 3.2 VisitorPass Lifecycle
| Current State | Event | Next State | Condition |
| :--- | :--- | :--- | :--- |
| `[INIT]` | `GENERATE` | `ACTIVE` | Generated on Host `APPROVE` |
| `ACTIVE` | `VALIDATE_OK` | `ACTIVE` | Valid pass, `valid_from <= now <= valid_to` |
| `ACTIVE` | `CHECKOUT` | `COMPLETED` | Session closed normally |
| `ACTIVE` | `EXPIRE` | `EXPIRED` | `now > valid_to` without active session |
| `ACTIVE` | `REVOKE` | `DEACTIVATED` | Admin/Host explicit revocation |

---

## 4. Permission List & `registry.py` Definition

```python
MODULE = "vms"

PERMISSIONS = [
    ("vms.visit_request.create", "Submit a new visitor pre-registration request"),
    ("vms.visit_request.view", "View accessible visitor requests"),
    ("vms.visit_request.decide", "Approve or reject assigned visitor requests"),
    ("vms.visitor_pass.view", "View visitor pass details and credentials"),
    ("vms.gate_session.validate", "Scan and validate visitor pass at gate terminals"),
    ("vms.gate_session.checkin", "Check in a visitor at a security gate"),
    ("vms.gate_session.checkout", "Check out a visitor at a security gate"),
    ("vms.blacklist.manage", "View, add, and deactivate blacklist records"),
    ("vms.audit.view", "View campus visitor operational audit logs"),
]

SYSTEM_PERMISSIONS = [
    "vms.schedule.sweep_expired",
]

SCOPE_PERMISSIONS = {
    "vms.visit_request.view": "host_user_id == current_user.pk or holds vms.audit.view",
    "vms.visit_request.decide": "host_user_id == current_user.pk",
}

_STUDENT = [
    "vms.visit_request.create",
    "vms.visit_request.view",
]

_FACULTY = [
    "vms.visit_request.create",
    "vms.visit_request.view",
    "vms.visit_request.decide",
    "vms.visitor_pass.view",
]

_STAFF = [
    "vms.visit_request.create",
    "vms.visit_request.view",
    "vms.visit_request.decide",
    "vms.visitor_pass.view",
]

_GUARD = [
    "vms.gate_session.validate",
    "vms.gate_session.checkin",
    "vms.gate_session.checkout",
    "vms.visitor_pass.view",
]

_ADMIN = [
    "vms.visit_request.create",
    "vms.visit_request.view",
    "vms.visit_request.decide",
    "vms.visitor_pass.view",
    "vms.gate_session.validate",
    "vms.gate_session.checkin",
    "vms.gate_session.checkout",
    "vms.blacklist.manage",
    "vms.audit.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "staff": _STAFF,
    "security_guard": _GUARD,
    "admin": _ADMIN,
}
```

---

## 5. Endpoint List & UI Route Guards

| Method | Path | Permission Required | Returns | Rules Enforced |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/vms/requests/` | None (Public) or `vms.visit_request.create` | `201 Created` (VisitRequestDTO) | VMS-BR-037, VMS-BR-051 |
| `GET` | `/api/v1/vms/requests/` | `vms.visit_request.view` | `200 OK` (List of VisitRequests) | Scope narrowing (404 on unowned) |
| `GET` | `/api/v1/vms/requests/{id}/` | `vms.visit_request.view` | `200 OK` (VisitRequestDetailDTO) | Scope check |
| `POST` | `/api/v1/vms/requests/{id}/decision/` | `vms.visit_request.decide` | `200 OK` (PassDTO if approved) | VMS-AFR-013-01, VMS-BR-052 |
| `POST` | `/api/v1/vms/passes/validate/` | `vms.gate_session.validate` | `200 OK` (ValidationVerdictDTO) | VMS-BR-077, VMS-BR-190, VMS-BR-191 |
| `POST` | `/api/v1/vms/passes/checkin/` | `vms.gate_session.checkin` | `200 OK` (SessionDTO) | VMS-AFR-018-01, BW-VMS-01 STT R3 |
| `POST` | `/api/v1/vms/sessions/{id}/checkout/`| `vms.gate_session.checkout`| `200 OK` (SessionDTO) | VMS-AFR-021-01, VMS-BR-105 |
| `GET` | `/api/v1/vms/blacklist/` | `vms.blacklist.manage` | `200 OK` (List of BlacklistDTO) | VMS-BR-051 |
| `POST` | `/api/v1/vms/blacklist/` | `vms.blacklist.manage` | `201 Created` | Admin authorization |
| `GET` | `/api/v1/vms/audit/` | `vms.audit.view` | `200 OK` (List of AuditLogs) | VMS-CFR-005 |

### 5.1 Client Navigation & Integration
* `Fusion-client` Navigation Registration:
  - `id`: `vms`
  - `label`: `Visitor Management`
  - `icon`: `ShieldCheck`
  - `to`: `/vms`
  - `section`: `Services`

---

## 6. Contracts & Dependencies

### Plural Contracts Exposed in `modules/vms/contracts.py`:
```python
def get_active_passes_for_hosts(host_user_ids: Sequence[int]) -> dict[int, list[VisitorPassDTO]]:
    """Returns active visitor passes grouped by host user_id."""
    ...

def get_visitor_sessions_by_dates(date_range: tuple[datetime, datetime]) -> list[VisitSessionDTO]:
    """Returns all campus visitor check-in/out sessions in the date window."""
    ...
```

---

## 7. Scheduled Work (Celery Beat)

* **Task Name:** `modules.vms.tasks.sweep_expired_visitor_passes`
* **Schedule:** Every hour (`crontab(minute=0)`)
* **Operation:**
  1. Marks pending `VisitRequest` records past scheduled end time as `EXPIRED` (`VMS-BR-062`).
  2. Updates `VisitorPass` records with `valid_to < now` and no active session from `ACTIVE` to `EXPIRED`.
* **Failure Impact:** If beat fails to run, expired passes would not be automatically flagged as expired in passive reports (though gate validation dynamic checks still intercept and reject them).

---

## 8. Open Questions & Pair Resolution

1. **Host Notification Dispatch:**  
   *Question:* Should notification dispatch to external SMS/email gateways block synchronous HTTP response?  
   *Resolution:* No. Notification dispatch is non-blocking via Celery worker or mocked adapter in `module-only` environment, ensuring API endpoints maintain sub-50ms latency.
2. **Offline Gate Contingency:**  
   *Question:* How should security gates handle transient network dropouts?  
   *Resolution:* Gate pass validation uses cryptographically signed QR payloads with local verification support (`VMS-BR-049`).

---
*(End of Blueprint)*
