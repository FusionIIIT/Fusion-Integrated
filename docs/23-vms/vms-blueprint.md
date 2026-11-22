# Architecture Blueprint: Visitor Management System (VMS)

- **Module Name**: Visitor Management System
- **Module Code**: `vms` (`modules/vms`)
- **Document Version**: 1.0 (Direct-Final)
- **Status**: APPROVED for implementation

---

## 1. Domain Entities & Database Schema

All database models inherit from `core.db.mixins.TimeStampedModel`. External users (Host, Staff, Operator, Admin) are referenced via integer `user_id` without cross-module foreign keys.

### 1.1 `Visitor`
Core identity record for external visitors.
- `id`: Auto-incrementing primary key.
- `name`: `CharField(max_length=150)`
- `email`: `EmailField(db_index=True)`
- `phone`: `CharField(max_length=20, db_index=True)`
- `organization`: `CharField(max_length=150, blank=True)`
- `id_document_type`: `CharField(max_length=30, choices=ID_DOCUMENT_TYPES)` (e.g., AADHAAR, PAN, PASSPORT, VOTER_ID, DRIVING_LICENSE)
- `id_document_number`: `CharField(max_length=100, db_index=True)`
- `is_vip`: `BooleanField(default=False)`
- `vip_reason`: `TextField(blank=True)`
- `created_at`, `updated_at`: `DateTimeField`

### 1.2 `VisitRequest`
Operational booking for a visit.
- `id`: Auto-incrementing primary key.
- `visitor`: `ForeignKey('Visitor', on_delete=models.PROTECT, related_name='visit_requests')`
- `host_id`: `PositiveIntegerField(db_index=True)` (User ID of the institute staff/faculty)
- `purpose`: `CharField(max_length=255)`
- `scheduled_start`: `DateTimeField(db_index=True)`
- `scheduled_end`: `DateTimeField(db_index=True)`
- `actual_check_in`: `DateTimeField(null=True, blank=True)`
- `actual_check_out`: `DateTimeField(null=True, blank=True)`
- `status`: `CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING_APPROVAL')`
  - Values: `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `EXPIRED`, `CANCELLED`, `CHECKED_IN`, `CHECKED_OUT`, `AUTO_CHECKED_OUT`, `TERMINATED_EARLY`
- `pass_type`: `CharField(max_length=30, choices=PASS_TYPES, default='PRE_REGISTERED')`
  - Values: `PRE_REGISTERED`, `WALK_IN`, `VIP`, `CONTRACTOR`, `EVENT`
- `access_zones`: `JSONField(default=list)` (List of allowed zone identifiers, e.g. `['Main Gate', 'Academic Block']`)
- `admin_notes`: `TextField(blank=True)`
- `rejection_reason`: `TextField(blank=True)`
- `is_urgent_exception`: `BooleanField(default=False)`
- `extension_hours`: `PositiveIntegerField(default=0)`

### 1.3 `Pass`
Authoritative digital pass with verifiable token and security credentials.
- `id`: Auto-incrementing primary key.
- `visit_request`: `OneToOneField('VisitRequest', on_delete=models.PROTECT, related_name='digital_pass')`
- `pass_number`: `CharField(max_length=64, unique=True, db_index=True)`
- `qr_token`: `CharField(max_length=128, unique=True, db_index=True)`
- `valid_from`: `DateTimeField()`
- `valid_to`: `DateTimeField()`
- `status`: `CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('USED', 'Used'), ('EXPIRED', 'Expired'), ('REVOKED', 'Revoked')], default='ACTIVE')`
- `issued_at`: `DateTimeField(auto_now_add=True)`

### 1.4 `GateCheckLog`
Audit log of all gate presentations, checks, entries, exits, and security overrides.
- `id`: Auto-incrementing primary key.
- `pass`: `ForeignKey('Pass', on_delete=models.PROTECT, related_name='check_logs')`
- `gate_name`: `CharField(max_length=100)`
- `checkpoint_type`: `CharField(max_length=20, choices=[('ENTRY', 'Entry Gate'), ('EXIT', 'Exit Gate'), ('ZONE_CHECK', 'Internal Zone Check')])`
- `action`: `CharField(max_length=20, choices=[('CHECK_IN', 'Check In'), ('CHECK_OUT', 'Check Out'), ('DENIED', 'Denied Entry'), ('OVERRIDE', 'Manual Override')])`
- `operator_id`: `PositiveIntegerField(null=True, blank=True)`
- `is_override`: `BooleanField(default=False)`
- `override_reason`: `TextField(blank=True)`
- `is_offline_sync`: `BooleanField(default=False)`
- `timestamp`: `DateTimeField(db_index=True)`

### 1.5 `HostPreAuthorization`
Recurring pre-authorizations granted by Hosts.
- `id`: Auto-incrementing primary key.
- `host_id`: `PositiveIntegerField(db_index=True)`
- `visitor_email`: `EmailField(db_index=True)`
- `visitor_name`: `CharField(max_length=150)`
- `valid_from`: `DateField()`
- `valid_to`: `DateField()`
- `is_active`: `BooleanField(default=True)`

### 1.6 `BlacklistEntry`
Centralized security watch/blacklist and temporary safe-list.
- `id`: Auto-incrementing primary key.
- `name`: `CharField(max_length=150)`
- `id_document_type`: `CharField(max_length=30)`
- `id_document_number`: `CharField(max_length=100, db_index=True)`
- `phone`: `CharField(max_length=20, db_index=True, blank=True)`
- `reason`: `TextField()`
- `status`: `CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('SAFE_LISTED', 'Safe-Listed'), ('INACTIVE', 'Inactive')], default='ACTIVE')`
- `safe_list_until`: `DateTimeField(null=True, blank=True)`
- `safe_list_reason`: `TextField(blank=True)`
- `safe_listed_by_id`: `PositiveIntegerField(null=True, blank=True)`

### 1.7 `EmergencyMusterRoster`
Snapshot of on-site visitors during emergency evacuation muster roll-call.
- `id`: Auto-incrementing primary key.
- `muster_id`: `CharField(max_length=64, db_index=True)`
- `assembly_point`: `CharField(max_length=100)`
- `initiated_by_id`: `PositiveIntegerField()`
- `initiated_at`: `DateTimeField(db_index=True)`
- `visitor`: `ForeignKey('Visitor', on_delete=models.PROTECT)`
- `pass`: `ForeignKey('Pass', on_delete=models.PROTECT)`
- `check_in_time`: `DateTimeField()`
- `accountability_status`: `CharField(max_length=20, choices=[('UNACCOUNTED', 'Unaccounted'), ('ACCOUNTED', 'Accounted')], default='UNACCOUNTED')`
- `accounted_at`: `DateTimeField(null=True, blank=True)`
- `accounted_by_id`: `PositiveIntegerField(null=True, blank=True)`

### 1.8 `AccessPolicy`
Versioned campus visitor access policies.
- `id`: Auto-incrementing primary key.
- `version`: `PositiveIntegerField(unique=True)`
- `visiting_hours_start`: `TimeField(default='08:00')`
- `visiting_hours_end`: `TimeField(default='20:00')`
- `max_duration_hours`: `PositiveIntegerField(default=12)`
- `is_published`: `BooleanField(default=False)`
- `published_at`: `DateTimeField(null=True, blank=True)`

---

## 2. State Machine & Lifecycle Transitions

```
[ Visitor Submits ]
        |
        v
 PENDING_APPROVAL --------(Host Reject)--------> REJECTED
        |
        +-----------------(Timeout / 24h)-----> EXPIRED
        |
        +-----------------(Host Approve / VIP / Pre-Auth)
        v
     APPROVED (Pass Active)
        |
        +-----------------(Early Revocation)---> TERMINATED_EARLY
        |
        v (Gate Scan / Check-In)
    CHECKED_IN (On-site)
        |
        +-----------------(Gate Exit)----------> CHECKED_OUT
        |
        +-----------------(Early Revocation)---> TERMINATED_EARLY
        |
        +-----------------(Nightly EOD Cutoff)-> AUTO_CHECKED_OUT (Overstay Flag)
```

---

## 3. Role Permissions & Authorization Model

Registered under module `vms`:
1. `Super Admin`:
   - `vms.role.manage`
   - `vms.vip.manage`
   - `vms.audit.view`
   - `vms.config.manage`
2. `Admin`:
   - `vms.policy.manage`
   - `vms.blacklist.manage`
   - `vms.analytics.view`
   - `vms.bulk.manage`
   - `vms.gate.override`
   - `vms.emergency.trigger`
   - `vms.visit.terminate`
   - `vms.contingency.approve`
3. `Security Personnel`:
   - `vms.gate.validate`
   - `vms.gate.checkin`
   - `vms.gate.checkout`
   - `vms.walkin.register`
   - `vms.dashboard.view`
   - `vms.zone.validate`
   - `vms.emergency.rollcall`
   - `vms.gate.offlinesync`
4. `Host`:
   - `vms.visit.decide`
   - `vms.preauth.manage`
   - `vms.visit.view_host`
   - `vms.visit.terminate_self`
5. `Visitor`:
   - `vms.visit.preregister`
   - `vms.pass.view_self`
   - `vms.visit.checkout_self`

---

## 4. API Endpoints

- `POST /api/v1/vms/visits/pre-register/`: Submit visit pre-registration.
- `GET /api/v1/vms/visits/`: List visits scoped to role (host, visitor, admin).
- `GET /api/v1/vms/visits/<id>/`: Retrieve visit details.
- `POST /api/v1/vms/visits/<id>/decide/`: Host approve/reject visit.
- `POST /api/v1/vms/visits/<id>/contingency-approve/`: Admin contingency approval.
- `POST /api/v1/vms/visits/<id>/extend/`: Admin/Host visit extension.
- `POST /api/v1/v1/vms/visits/<id>/terminate/`: Early termination.
- `POST /api/v1/vms/visits/bulk/`: Bulk visitor registration.
- `POST /api/v1/vms/visits/walk-in/`: Walk-in registration at security gate.
- `GET /api/v1/vms/passes/<id>/`: Retrieve digital pass and QR code token.
- `POST /api/v1/vms/gate/validate/`: Validate pass at gate.
- `POST /api/v1/vms/gate/check-in/`: Perform gate check-in.
- `POST /api/v1/vms/gate/check-out/`: Perform gate check-out.
- `POST /api/v1/vms/gate/override/`: Admin manual gate override.
- `POST /api/v1/vms/gate/offline-sync/`: Security offline batch sync.
- `GET /api/v1/vms/dashboard/live/`: Live on-site visitor roster.
- `POST /api/v1/vms/zones/validate/`: Validate zone access.
- `POST /api/v1/vms/zones/elevate/`: Grant temporary zone elevation.
- `GET /api/v1/vms/blacklist/`: List blacklist entries.
- `POST /api/v1/vms/blacklist/`: Add blacklist entry.
- `POST /api/v1/vms/blacklist/<id>/safe-list/`: Grant temporary safe-list.
- `POST /api/v1/vms/emergency/muster/`: Trigger emergency muster.
- `GET /api/v1/vms/emergency/roster/`: Get active muster roster.
- `POST /api/v1/vms/emergency/roll-call/`: Mark visitor roll-call status.
- `GET /api/v1/vms/analytics/dashboard/`: Visitor traffic statistics.
- `GET /api/v1/vms/audit/`: Operational audit trail.
- `GET/POST /api/v1/vms/policies/`: Manage versioned access policies.
- `GET/POST /api/v1/vms/pre-authorizations/`: Host pre-authorizations.

---

## 5. Architectural Guardrails
1. **Pure Domain**: `modules/vms/domain/` contains zero framework imports (`django`, `rest_framework`, `celery`).
2. **Selectors**: Read-only queries with strict caller role-scoping.
3. **Services**: All write operations wrapped in `@transaction.atomic` using `select_for_update()` to prevent race conditions on pass usage and approval transitions.
4. **Public Contracts**: `contracts.py` exposes plural, read-only DTO functions without foreign key leakage.
