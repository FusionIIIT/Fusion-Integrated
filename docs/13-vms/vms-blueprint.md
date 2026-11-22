# Visitor Management System (VMS) — Module Blueprint

**Module Name**: Visitor Management System  
**Module Code**: `vms`  
**Docs Folder**: `docs/13-vms/`  
**Author**: Krishna Rai (Student 1 - Builder)  
**Reviewer**: Ankita Jaiswal (Student 2 - Tester & Reviewer)  
**Status**: APPROVED BY STUDENT 2  
**Date**: 2026-11-22  

---

## 1. Traceability Table (Step 3.1)

| Spec ID | Type | Description | Target Layer & File | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| `VMS-CFR-001` | CFR | Visitor Registration & Host Approval | `services/registration.py` | `test_services.py::test_registration_lifecycle` |
| `VMS-CFR-002` | CFR | Pass Issuance & QR Validation | `services/gate.py`, `domain/rules.py` | `test_services.py::test_pass_generation` |
| `VMS-CFR-003` | CFR | Gate Check-in & Check-out Logging | `services/gate.py`, `models/visit.py` | `test_gate.py::test_check_in_out` |
| `VMS-CFR-004` | CFR | Blacklist / Watchlist Enforcement | `domain/rules.py`, `services/security.py` | `test_domain.py::test_blacklist_refusal` |
| `VMS-CFR-005` | CFR | Overstay Detection & Alerts | `tasks.py`, `services/security.py` | `test_schedule.py::test_overstay_task` |
| `VMS-CFR-006` | CFR | Emergency Muster & Roll-call | `services/security.py`, `models/emergency.py`| `test_services.py::test_emergency_muster` |
| `VMS-BR-001` | BR | Exact Quorum Matching for Blacklist | `domain/rules.py` | `test_domain.py::test_blacklist_matching` |
| `VMS-BR-004` | BR | Blocking Pass Registration on Blacklist | `services/registration.py` | `test_services.py::test_blacklist_blocks_pass` |
| `VMS-BR-017` | BR | Same-day Duplicate Active Pass Prevention| `domain/rules.py`, `services/registration.py` | `test_services.py::test_no_duplicate_same_day` |
| `VMS-BR-023` | BR | No Duplicate Checkout Allowed | `domain/state_machine.py`, `services/gate.py`| `test_gate.py::test_no_duplicate_checkout` |
| `VMS-BR-032` | BR | Walk-in Pass Default 4-Hour Duration | `domain/rules.py`, `services/registration.py` | `test_domain.py::test_walkin_duration` |
| `VMS-BR-041` | BR | Zone Access Authorization & Rejection | `domain/rules.py`, `services/gate.py` | `test_domain.py::test_zone_access` |
| `VMS-BR-045` | BR | Overstay Eviction & Muster Alerts | `services/security.py`, `tasks.py` | `test_schedule.py::test_muster_overstay` |
| `BW-VMS-01` | WF | Pre-registered Approved Visit Lifecycle | `domain/state_machine.py`, `services/gate.py`| `test_journey.py::test_approved_visit_journey` |
| `BW-VMS-02` | WF | Pre-registered Rejected Visit | `domain/state_machine.py`, `services/registration.py` | `test_journey.py::test_rejected_visit_journey` |
| `BW-VMS-06` | WF | Walk-in Host-approved Visit | `services/registration.py`, `services/gate.py`| `test_journey.py::test_walkin_flow` |
| `BW-VMS-11` | WF | Offline Gate Entry & Reconciliation | `services/gate.py`, `api/views.py` | `test_api.py::test_offline_reconciliation` |

---

## 2. Domain Model & Entities (Step 3.2)

### Aggregate 1: Visitor
- `id`: BigAutoField (Primary Key)
- `first_name`: CharField(max_length=64)
- `last_name`: CharField(max_length=64)
- `email`: EmailField
- `phone`: CharField(max_length=20, db_index=True)
- `id_type`: CharField(choices=[Aadhaar, Passport, DrivingLicense, VoterId])
- `id_number_hash`: CharField(max_length=64, db_index=True) — SHA-256 hash for exact matching
- `organization`: CharField(max_length=128, blank=True)
- `is_active`: BooleanField(default=True)
- `created_at`, `updated_at`: DateTimeField (UTC)

### Aggregate 2: Visit & Pass
- `id`: BigAutoField (Primary Key)
- `visitor`: ForeignKey(Visitor, on_delete=CASCADE, related_name='visits')
- `host_user_id`: IntegerField(db_index=True) — Canonical user ID from IAM/Directory
- `purpose`: CharField(max_length=255)
- `visit_type`: CharField(choices=[pre_registered, walk_in, vip, contractor])
- `status`: CharField(choices=[requested, approved, rejected, cancelled, on_site, completed, expired])
- `pass_number`: CharField(max_length=32, unique=True, db_index=True) — e.g. `PASS-YYYYMMDD-XXXX`
- `qr_code_hash`: CharField(max_length=64, unique=True, db_index=True)
- `valid_from`: DateTimeField
- `valid_to`: DateTimeField
- `allowed_zones`: JSONField (list of zone codes, e.g. `['MAIN_GATE', 'ACADEMIC_BLOCK']`)
- `check_in_time`: DateTimeField(null=True, blank=True)
- `check_out_time`: DateTimeField(null=True, blank=True)
- `checked_in_by`: IntegerField(null=True, blank=True) — Security guard user ID
- `checked_out_by`: IntegerField(null=True, blank=True)

### Aggregate 3: Security & Alerts
- `BlacklistEntry`:
  - `id_type`, `id_number_hash`, `full_name`, `phone`, `reason`, `severity`, `is_active`, `added_by`
- `GateAlert`:
  - `visit_id`, `visitor_id`, `alert_type` (blacklist_attempt, zone_violation, overstay, unauthorized_entry), `severity` (info, warning, critical), `status` (open, resolved), `resolved_by`
- `EmergencyMuster`:
  - `muster_code`, `status` (active, resolved), `triggered_by`, `headcount_total`, `headcount_accounted`, `started_at`, `ended_at`

---

## 3. State Machine (Step 3.3)

```text
       [Submit Request]
             │
             ▼
        [REQUESTED]
        │         │
[Host Approve]   [Host Reject / Timeout]
        │         │
        ▼         ▼
    [APPROVED]  [REJECTED] (terminal)
        │
[Gate Check-in] ──(Pass Expired)──► [EXPIRED] (terminal)
        │
        ▼
    [ON_SITE]
        │
[Gate Check-out / Auto Checkout]
        │
        ▼
   [COMPLETED] (terminal)
```

**Terminal States**: `REJECTED`, `CANCELLED`, `COMPLETED`, `EXPIRED`.  
**Choke Point**: Single transactional state transition service `services.gate.transition_visit_state()` enforcing lock with `select_for_update()`.

---

## 4. Permissions & Navigation (Step 3.4)

### Module Grant
- `vms.access` — Base module access grant

### Permissions Catalog
- `vms.visit.create` — Submit visit requests (Student, Faculty, Staff, Public Guest)
- `vms.visit.approve` — Approve/reject hosted visits (Faculty, Staff)
- `vms.gate.scan` — Scan QR, check-in, check-out, register walk-in (Security Personnel)
- `vms.security.admin` — Manage blacklists, override denials, view alerts (Security Officer, Admin)
- `vms.emergency.muster` — Trigger and manage emergency roll-call (Chief Security Officer, Dean)

### Navigation Items
1. **Passes / My Visits** (`/vms/my-visits`) &rarr; `vms.visit.create`
2. **Approval Queue** (`/vms/approvals`) &rarr; `vms.visit.approve`
3. **Gate Terminal** (`/vms/gate-scanner`) &rarr; `vms.gate.scan`
4. **Security & Alerts** (`/vms/security`) &rarr; `vms.security.admin`
5. **Emergency Muster** (`/vms/muster`) &rarr; `vms.emergency.muster`

---

## 5. Endpoints & API Transport (Step 3.5)

| HTTP Method | Path | Permission Required | Throttle Scope | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/vms/visitors/` | `vms.visit.create` | `vms_register` | Create visitor profile |
| `GET` | `/api/v1/vms/visits/` | `vms.visit.create` | `vms_read` | List visible visits (scoped) |
| `POST` | `/api/v1/vms/visits/` | `vms.visit.create` | `vms_register` | Submit visit request |
| `POST` | `/api/v1/vms/visits/{id}/approve/` | `vms.visit.approve` | `vms_write` | Host approves visit |
| `POST` | `/api/v1/vms/visits/{id}/reject/` | `vms.visit.approve` | `vms_write` | Host rejects visit |
| `POST` | `/api/v1/vms/gate/verify-qr/` | `vms.gate.scan` | `vms_gate` | Verify QR hash at gate |
| `POST` | `/api/v1/vms/gate/check-in/` | `vms.gate.scan` | `vms_gate` | Log gate check-in |
| `POST` | `/api/v1/vms/gate/check-out/` | `vms.gate.scan` | `vms_gate` | Log gate check-out |
| `POST` | `/api/v1/vms/gate/reconcile-offline/` | `vms.gate.scan` | `vms_gate` | Batch sync offline logs |
| `GET` | `/api/v1/vms/security/alerts/` | `vms.security.admin` | `vms_read` | View security alerts |
| `POST` | `/api/v1/vms/security/blacklist/` | `vms.security.admin` | `vms_write` | Add blacklist entry |
| `POST` | `/api/v1/vms/emergency/muster/` | `vms.emergency.muster` | `vms_write` | Trigger muster roll-call |

---

## 6. Contracts Surface (Step 3.6)

Exposed via `modules/vms/contracts.py`:
- `get_active_visitors_on_campus() -> list[ActiveVisitorDTO]`
- `get_visitor_clearance_status(id_number_hash: str) -> VisitorClearanceDTO`
- `is_host_currently_entertaining_guests(user_id: int) -> bool`

---

## 7. Scheduled Work (Step 3.7)

Registered in `config/celery.py` via `modules.vms.schedule`:
- `vms-check-overstay-visitors`: Runs every 10 minutes &rarr; marks overstays and generates `GateAlert`.
- `vms-expire-stale-requests`: Runs daily at 00:00 &rarr; expires unapproved requests whose date has passed.

---

## 8. Open Questions & Waivers (Step 3.8)
- **Q1**: How to handle multi-entry contractor passes?  
  *Decision*: Multiple check-ins allowed within valid date range if `is_multi_entry=True`. Default is single entry.
- **Q2**: Should gate scanner require biometric verification?  
  *Decision*: Hardware biometric verification is out of scope for the software ERP; validated via QR token and photo/ID check at the gate.
