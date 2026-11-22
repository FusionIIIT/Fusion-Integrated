# VMS implementation blueprint

## Approval and scope record

The user explicitly instructed on 2026-11-22 to assume Student 2 approves all required gates and to continue through implementation. This records the user's instruction; it is not represented as a separate message from Student 2. No commit, push, or pull request is authorized. The assigned docs folder number was not supplied; `09` is selected as the next unused top-level docs number. The spec uses VMS IDs; the implementation module code and route segment are lowercase `vms`.

- Module: Visitor Management System (VMS).
- Spec source: the supplied VMS v1.2/v1.3 artifacts.
- Environment: module-only.
- Branch: `module/vms`, from `upstream/main`.
- Reference module: `modules/placement`.
- User-approved working assumptions: exact actor labels `Super Admin`, `Admin`, and `Security Personnel` are treated as IAM designation names; `Host` maps to `faculty` and `staff`; Visitor is an external visitor profile accessed using a high-entropy, emailed, single-purpose access credential. Blacklist checks use case-insensitive exact normalized name or keyed document fingerprint; active blacklist denials are never manually overridden. Approval reminders default to 12 and 20 hours, configurable on an immutable policy version. `CANCELLED` is represented as a valid state but no cancellation transition is exposed. These decisions are recorded as conservative implementation assumptions for Student 2 to review.

## Phase 0 inventory

- 33 CFRs and 225 AFRs; AFR IDs are VMS-AFR-002 through VMS-AFR-226.
- 47 active reusable business rules. The final rule artifact identifies no retired BR IDs.
- 39 active use cases. VMS-UC-029 is retired because it described internal behavior, not an actor goal; its identity is not reused.
- 23 Basis Workflows and 7 Composite Workflows.
- 5 clarification records: ISS-VMS-016/017 (blacklist matching), ISS-VMS-018 (reminder timing), ISS-VMS-019 (CANCELLED state), and ISS-VMS-023 (gate override eligibility).
- The AFR_RTM sheet's UC/BR/WF representation columns are empty. Coverage below is therefore mapped from the requirements and governing BR/UC/WF specifications, not inferred from empty cells.
- Boundary: VMS owns visitor workflow and records. IAM owns institutional identities and RBAC. External directory, campus ID, Event Management, Hostel Management, Access Control, notification transport, and physical security infrastructure remain outside VMS.

## Phase 1 domain and identity

VMS is one bounded context. Host references are plain `host_user_id` values and are hydrated in batches through `modules.directory.contracts`; no cross-module FK or ERP database access is allowed. External visitors are VMS-owned profiles, never IAM users. Host scope is enforced in selectors; admin/security access is enforced by the active permission set, with object reads narrowed before lookup. The lifecycle has explicit, transactional transitions and append-only visit logs/audit records. Policies and blacklist registries are versioned; only published versions govern new operations. Scheduled work expires pending requests, sends reminders, checks time-boxed permissions, auto-checks out expired on-site visits, and retries outbox deliveries. No money/quota ledger is required.

## Traceability table

Each live identifier has a planned enforcement point. The owning service is the transactional choke point; the API only parses, authorizes, and serializes. Route-to-service details follow the module's `/api/v1/vms/` endpoint list in the implementation.

| ID | Requirement / behavior | Enforcement point | Spec status |
|---|---|---|---|
| `VMS-CFR-001` | System-service (AFRs: VMS-AFR-002) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-002` | Actor-service + Rule/Constraint (AFRs: VMS-AFR-003, VMS-AFR-177, VMS-AFR-178, VMS-AFR-179, VMS-AFR-180, VMS-AFR-181, VMS-AFR-182, VMS-AFR-183, VMS-AFR-184, VMS-AFR-185) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-003` | Integration + Scope (AFRs: VMS-AFR-004, VMS-AFR-007, VMS-AFR-217, VMS-AFR-218, VMS-AFR-219, VMS-AFR-222, VMS-AFR-223, VMS-AFR-224, VMS-AFR-225, VMS-AFR-226) | `modules/vms/services/configuration.py; modules/vms/api/views.py`; see constituent AFR rows | Active |
| `VMS-CFR-004` | Actor-service + Authorization (AFRs: VMS-AFR-005, VMS-AFR-072, VMS-AFR-196, VMS-AFR-197) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-005` | Information-access + Data/Record (AFRs: VMS-AFR-006, VMS-AFR-216) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-006` | Actor-service + Rule/Constraint (AFRs: VMS-AFR-008, VMS-AFR-121, VMS-AFR-122, VMS-AFR-123, VMS-AFR-124, VMS-AFR-125, VMS-AFR-126, VMS-AFR-127, VMS-AFR-128, VMS-AFR-129, VMS-AFR-204, VMS-AFR-215) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-007` | Actor-service + Rule/Constraint (AFRs: VMS-AFR-009, VMS-AFR-106, VMS-AFR-107, VMS-AFR-108, VMS-AFR-109, VMS-AFR-110, VMS-AFR-111, VMS-AFR-118, VMS-AFR-119, VMS-AFR-120, VMS-AFR-205, VMS-AFR-214) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-008` | Information-access (AFRs: VMS-AFR-010, VMS-AFR-142, VMS-AFR-143, VMS-AFR-144, VMS-AFR-145, VMS-AFR-146, VMS-AFR-147, VMS-AFR-148, VMS-AFR-149, VMS-AFR-150, VMS-AFR-151, VMS-AFR-152, VMS-AFR-153) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-009` | Actor-service + Workflow/progression (AFRs: VMS-AFR-011, VMS-AFR-012, VMS-AFR-060, VMS-AFR-061, VMS-AFR-154, VMS-AFR-155, VMS-AFR-156, VMS-AFR-157, VMS-AFR-158, VMS-AFR-159, VMS-AFR-160, VMS-AFR-161, VMS-AFR-162, VMS-AFR-163) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-010` | Actor-service + Workflow/progression (AFRs: VMS-AFR-013, VMS-AFR-014, VMS-AFR-015, VMS-AFR-016, VMS-AFR-017, VMS-AFR-052, VMS-AFR-054, VMS-AFR-055, VMS-AFR-056, VMS-AFR-057, VMS-AFR-058, VMS-AFR-059, VMS-AFR-063, VMS-AFR-064) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-011` | Actor-service + Authorization (AFRs: VMS-AFR-018, VMS-AFR-195) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-012` | Notification + Information-access (AFRs: VMS-AFR-019) | `modules/vms/services/scheduled.py; modules/vms/tasks.py`; see constituent AFR rows | Active |
| `VMS-CFR-013` | Actor-service + Rule/Constraint + Workflow/progression (AFRs: VMS-AFR-020, VMS-AFR-075, VMS-AFR-076, VMS-AFR-077, VMS-AFR-078, VMS-AFR-080, VMS-AFR-082, VMS-AFR-083, VMS-AFR-084, VMS-AFR-190) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-014` | Actor-service + Authorization (AFRs: VMS-AFR-024, VMS-AFR-085) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-015` | Actor-service + Data/Record + Workflow/progression (AFRs: VMS-AFR-021, VMS-AFR-081, VMS-AFR-097, VMS-AFR-099, VMS-AFR-100, VMS-AFR-105, VMS-AFR-212) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-016` | Actor-service + Workflow/progression (AFRs: VMS-AFR-022, VMS-AFR-031, VMS-AFR-044, VMS-AFR-045, VMS-AFR-046, VMS-AFR-047, VMS-AFR-049, VMS-AFR-050, VMS-AFR-053) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-017` | Information-access (AFRs: VMS-AFR-023, VMS-AFR-092, VMS-AFR-093) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-018` | Actor-service + Workflow/progression + Notification (AFRs: VMS-AFR-025, VMS-AFR-130, VMS-AFR-131, VMS-AFR-132, VMS-AFR-133, VMS-AFR-134, VMS-AFR-135, VMS-AFR-136, VMS-AFR-137, VMS-AFR-138, VMS-AFR-139, VMS-AFR-140, VMS-AFR-141) | `modules/vms/services/scheduled.py; modules/vms/tasks.py`; see constituent AFR rows | Active |
| `VMS-CFR-019` | Actor-service + Workflow/progression (AFRs: VMS-AFR-026, VMS-AFR-032, VMS-AFR-033, VMS-AFR-034, VMS-AFR-035, VMS-AFR-036, VMS-AFR-037, VMS-AFR-038, VMS-AFR-040, VMS-AFR-041) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-020` | System-service + Information-access (AFRs: VMS-AFR-027, VMS-AFR-042, VMS-AFR-043, VMS-AFR-065, VMS-AFR-066, VMS-AFR-067, VMS-AFR-068, VMS-AFR-069, VMS-AFR-070, VMS-AFR-071, VMS-AFR-210, VMS-AFR-211) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-021` | Information-access (AFRs: VMS-AFR-028, VMS-AFR-029, VMS-AFR-030) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-022` | System-service + Trigger/Time (AFRs: VMS-AFR-062, VMS-AFR-198, VMS-AFR-199, VMS-AFR-200, VMS-AFR-201) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-023` | Actor-service + System-service + Workflow/progression (AFRs: VMS-AFR-098, VMS-AFR-101, VMS-AFR-102) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-024` | Actor-service + Authorization + Workflow/progression (AFRs: VMS-AFR-073, VMS-AFR-074, VMS-AFR-103, VMS-AFR-104) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-025` | Actor-service + System-service + Workflow/progression (AFRs: VMS-AFR-086, VMS-AFR-087) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-026` | Actor-service + Rule/Constraint + Workflow/progression (AFRs: VMS-AFR-088, VMS-AFR-089, VMS-AFR-090, VMS-AFR-091, VMS-AFR-094, VMS-AFR-095, VMS-AFR-096, VMS-AFR-191, VMS-AFR-192, VMS-AFR-213) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-027` | Rule/Constraint + Notification (AFRs: VMS-AFR-039, VMS-AFR-048, VMS-AFR-051, VMS-AFR-079, VMS-AFR-112, VMS-AFR-113, VMS-AFR-114, VMS-AFR-115, VMS-AFR-116, VMS-AFR-117, VMS-AFR-188, VMS-AFR-189) | `modules/vms/services/scheduled.py; modules/vms/tasks.py`; see constituent AFR rows | Active |
| `VMS-CFR-028` | System-service + Notification (AFRs: VMS-AFR-164, VMS-AFR-165, VMS-AFR-166, VMS-AFR-167, VMS-AFR-168, VMS-AFR-169, VMS-AFR-170, VMS-AFR-171, VMS-AFR-172, VMS-AFR-173, VMS-AFR-174, VMS-AFR-175, VMS-AFR-176, VMS-AFR-220, VMS-AFR-221) | `modules/vms/services/scheduled.py; modules/vms/tasks.py`; see constituent AFR rows | Active |
| `VMS-CFR-029` | Rule/Constraint + Data/Record (AFRs: VMS-AFR-186, VMS-AFR-187) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-030` | Rule/Constraint + Actor-service (AFRs: VMS-AFR-193, VMS-AFR-194) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-031` | Rule/Constraint + Actor-service + Workflow/progression (AFRs: VMS-AFR-202, VMS-AFR-203) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `VMS-CFR-032` | Data/Record + Integration (AFRs: VMS-AFR-206, VMS-AFR-207) | `modules/vms/services/configuration.py; modules/vms/api/views.py`; see constituent AFR rows | Active |
| `VMS-CFR-033` | Data/Record (AFRs: VMS-AFR-208, VMS-AFR-209) | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py`; see constituent AFR rows | Active |
| `BW-VMS-01` | Pre-registered Approved Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-02` | Pre-registered Rejected Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-03` | Pre-registered Approval Timeout | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-04` | Pre-authorized Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-05` | VIP Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-06` | Walk-in Host-approved Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-07` | Walk-in Contingency-approved Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-08` | Walk-in Host-rejected Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-09` | Gate Validation Denied | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-10` | Gate Denial with Authorized Override | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-11` | Offline Gate Entry and Reconciliation | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-12` | Zone Access Granted | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-13` | Zone Access Denied and Alert Handled | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-14` | Temporary Zone Elevation and One Re-validation | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-15` | Host Terminates Pass Before Check-in | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-16` | Host Terminates On-site Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-17` | Admin Terminates Pass Before Check-in | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-18` | Admin Terminates On-site Visit | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-19` | Admin-triggered Emergency Muster | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-20` | Security-triggered Emergency Muster | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-21` | Bulk Event Visitor Entry | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-22` | Same-day Urgent Pre-registration | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `BW-VMS-23` | Admin-approved Visit Extension | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-01` | Pre-registered Visit Lifecycle | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-02` | Walk-in Visit Lifecycle | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-03` | Gate Entry Validation and Exception Handling | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-04` | Zone Access and Elevation | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-05` | Early Termination and Extension | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-06` | Emergency Muster and Accountability | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `CW-VMS-07` | Bulk Event Visitor Handling | `modules/vms/domain/state_machine.py; modules/vms/services/visits.py or modules/vms/services/security.py` | Active |
| `VMS-AFR-002` | VMS shall provide a single authoritative system for visitor-related records that replaces manual entry-point registers, email, phone, and paper-based processes. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-003` | VMS shall allow the Super Admin to assign and manage Admin and Security Personnel roles for specified zones or durations. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-004` | VMS shall allow the Super Admin to configure system-wide integration settings with campus ID systems. | `modules/vms/services/configuration.py; AuditEvent` | Partial (settings are recorded; no campus ID connector contract is available) |
| `VMS-AFR-005` | VMS shall allow the Super Admin to manage special permissions for VIP visitors. | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-AFR-006` | VMS shall maintain audit-trail information for security reviews. | `modules/vms/models/visits.py; modules/vms/api/views.py` | Active |
| `VMS-AFR-007` | VMS shall support coordination of visitor data with Hostel Management and Event Management only as explicitly defined integration points. | `modules/vms/services/configuration.py; AuditEvent` | Partial (settings are recorded; external contracts are unavailable) |
| `VMS-AFR-008` | VMS shall allow Admin to configure access policies including visiting hours, maximum duration, and restricted zones. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-009` | VMS shall allow Admin to maintain the blacklist/watchlist registry. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-010` | VMS shall allow Admin to generate visitor statistics and compliance reports. | `modules/vms/selectors/reports.py` | Active |
| `VMS-AFR-011` | VMS shall allow Admin to coordinate special-event visitor management requiring large-scale visitor handling. | `modules/vms/services/configuration.py; existing approved visits only` | Partial |
| `VMS-AFR-012` | VMS shall allow Admin to review and manage bulk approval workflows. | `modules/vms/services/configuration.py; import does not bulk-approve pending Host requests` | Partial |
| `VMS-AFR-013` | VMS shall notify Hosts about pending visit requests requiring their decision. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-014` | VMS shall allow Hosts to approve or reject visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-015` | VMS shall allow Hosts to apply optional zone restrictions to approved visit requests. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-016` | VMS shall allow Hosts to apply optional time restrictions to approved visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-017` | VMS shall allow Hosts to record special instructions for approved visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-018` | VMS shall allow Hosts to pre-authorize regular visitors such as project collaborators, vendors, and parents. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-019` | VMS shall notify Hosts about visitor arrival in real time. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-020` | VMS shall allow Security Personnel to validate visitor identity and passes at gate checkpoints. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-021` | VMS shall allow Security Personnel to log visitor entry and exit using QR or OTP scanning. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-022` | VMS shall allow Security Personnel to perform on-spot registration for walk-in visitors. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-023` | VMS shall provide live visitor tracking dashboards to Security Personnel. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-024` | VMS shall allow Security Personnel to escalate suspicious cases to administrators. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-025` | VMS shall allow Security Personnel to generate emergency evacuation reports. | `modules/vms/selectors/reports.py` | Active |
| `VMS-AFR-026` | VMS shall allow Visitors to pre-register online by specifying purpose, host, date/time, and uploading ID documents. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-027` | VMS shall deliver a digital pass with a unique QR or barcode to an approved Visitor for gate entry. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-028` | VMS shall allow Visitors to track approval status of their visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-029` | VMS shall allow Visitors to view their visit history. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-030` | VMS shall notify Visitors about appointment-related events. | `modules/vms/services/visits.py; appointment lifecycle email outbox` | Active |
| `VMS-AFR-031` | VMS shall support walk-in visitor registration at the gate through Security Personnel assistance. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-032` | VMS shall capture visitor personal details during online pre-registration. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-033` | VMS shall capture visit purpose during online pre-registration. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-034` | VMS shall capture host selection during online pre-registration. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-035` | VMS shall capture visit schedule during online pre-registration. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-036` | VMS shall accept visitor ID documents during online pre-registration. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-037` | VMS shall validate submitted pre-registration fields before accepting a visit request. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-038` | VMS shall check online pre-registration submissions for duplicate requests. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-039` | VMS shall check online pre-registration submissions against watchlist records. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-040` | VMS shall create a visit request with Pending status after a valid pre-registration submission. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-041` | VMS shall notify the selected Host after a pending visit request is created. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-042` | VMS shall issue a digital pass only after approval of the visit request. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-043` | VMS shall deliver an issued digital pass through email, SMS, or app notification. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-044` | VMS shall allow Security Personnel to register walk-in visitors at gate checkpoints. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-045` | VMS shall allow Security Personnel to capture walk-in visitor details. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-046` | VMS shall allow Security Personnel to scan or enter walk-in visitor ID details. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-047` | VMS shall allow Security Personnel to select the Host for a walk-in visitor quick approval request. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-048` | VMS shall perform an immediate blacklist check before issuing a temporary badge for a walk-in visitor. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-049` | VMS shall allow contingency approval by the relevant Admin when the selected Host is unavailable for a walk-in visit. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-050` | VMS shall apply the configured SLA to contingency approval for host-unavailable walk-in visits. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-051` | VMS shall reject registration requests that match the blacklist registry. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-052` | VMS shall require explicit Host approval before issuing a pass for a pre-registered visit. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-053` | VMS shall enforce the configured walk-in pass duration for walk-in passes, with the default duration treated as 4 hours. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-054` | VMS shall send push notifications to Hosts for pending visit requests. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-055` | VMS shall allow Hosts to approve pending visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-056` | VMS shall allow Hosts to reject pending visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-057` | VMS shall allow Hosts to add zone restrictions while deciding a request. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-058` | VMS shall allow Hosts to modify the visit time window while deciding a request. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-059` | VMS shall allow Hosts to add special instructions while deciding a request. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-060` | VMS shall support bulk approval for recurring vendors. | `modules/vms/services/configuration.py; only approved visit references can be assigned` | Partial |
| `VMS-AFR-061` | VMS shall support bulk approval for scheduled events. | `modules/vms/services/configuration.py; only approved visit references can be assigned` | Partial |
| `VMS-AFR-062` | VMS shall automatically expire pending requests after the policy-defined window, with the default window treated as 24 hours. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-063` | VMS shall update the visit request status after a Host approval or rejection decision. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-064` | VMS shall notify the Visitor and Security Personnel after Host approval or rejection decisions. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-065` | VMS shall generate a visitor pass after a visit request is approved. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-066` | VMS shall include a unique QR code in each generated pass. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-067` | VMS shall include a one-time OTP for manual verification in each generated pass. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-068` | VMS shall include valid-from and valid-until timestamps in each generated pass. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-069` | VMS shall include permitted zones in each generated pass. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-070` | VMS shall classify approved pre-registration passes as PRE_REGISTERED pass type. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-071` | VMS shall classify on-spot registration passes as WALK_IN pass type. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-072` | VMS shall classify special visitors approved by Super Admin override as VIP pass type. | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-AFR-073` | VMS shall allow a Host to deactivate a visitor pass early for policy breaches. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-074` | VMS shall allow an Admin to deactivate a visitor pass early for policy breaches. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-075` | VMS shall allow Security Personnel to scan a visitor QR code at a gate checkpoint. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-076` | VMS shall allow Security Personnel to verify a visitor OTP at a gate checkpoint. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-077` | VMS shall validate that a pass is active before allowing gate entry. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-078` | VMS shall validate that gate entry occurs within the pass validity window. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-079` | VMS shall perform a real-time blacklist check during gate check-in. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-080` | VMS shall validate zone permissions during gate entry where zone permission is relevant to the checkpoint. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-081` | VMS shall log approved entry with timestamp, entry point, and device ID. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-082` | VMS shall block visitor entry when gate validation fails. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-083` | VMS shall record the reason when gate validation fails. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-084` | VMS shall generate alerts for flagged visitors during failed gate validation. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-085` | VMS shall allow Admin manual override of gate validation failures only with recorded justification. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-086` | VMS shall cache offline gate entries when connectivity is unavailable. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-087` | VMS shall synchronize cached offline gate entries when connectivity is restored. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-088` | VMS shall enforce zone-level permissions for visitors. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-089` | VMS shall support door-reader validation of visitor token or QR against zone policy. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-090` | VMS shall log zone access allowed events in real time. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-091` | VMS shall log zone access denied events in real time. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-092` | VMS shall display an on-site visitor roster in Admin dashboards. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-093` | VMS shall display visitor zone movements in Admin dashboards. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-094` | VMS shall generate geofenced alerts for out-of-bounds visitor movement. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-095` | VMS shall allow Admin to grant temporary zone elevation for a visitor. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-096` | VMS shall require temporary zone elevation to be time-boxed. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-097` | VMS shall allow Security Personnel to scan a visitor badge for checkout. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-098` | VMS shall allow a Visitor to check out using kiosk or app when such interface is available. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-099` | VMS shall log visitor exit time during checkout. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-100` | VMS shall update the on-site roster after visitor checkout. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-101` | VMS shall automatically check out a visitor when the scheduled validity ends. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-102` | VMS shall automatically check out a visitor when the pass expires. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-103` | VMS shall allow Host to terminate a visit early for policy breaches. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-104` | VMS shall allow Admin to terminate a visit early for policy breaches. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-105` | VMS shall mark a visit as Completed with accurate in-time and out-time after exit is recorded. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-106` | VMS shall allow Admin to maintain blacklist records containing visitor name. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-107` | VMS shall allow Admin to maintain blacklist records containing visitor ID number. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-108` | VMS shall allow Admin to maintain blacklist records containing visitor phone and email. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-109` | VMS shall allow Admin to record a reason for blacklisting. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-110` | VMS shall allow Admin to assign a severity level to each blacklist record. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-111` | VMS shall allow Admin to assign an optional expiry date to a blacklist record. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-112` | VMS shall perform blacklist checks during pre-registration submission. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-113` | VMS shall perform blacklist checks during walk-in registration. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-114` | VMS shall perform blacklist checks during gate check-in. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-115` | VMS shall immediately reject a request when the visitor identity matches a blacklist record. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-116` | VMS shall immediately reject an entry attempt when the visitor identity matches a blacklist record. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-117` | VMS shall send alerts to security authorities when a blacklist match is detected. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-118` | VMS shall support a temporary safe-list for vetted VIPs and vendors. | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-AFR-119` | VMS shall require each temporary safe-list entry to have an expiry. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-120` | VMS shall consume only published versions of the blacklist registry at runtime. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-121` | VMS shall allow Admin to configure visiting-hours start and end time. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-122` | VMS shall allow Admin to configure maximum visit duration. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-123` | VMS shall allow Admin to configure restricted access zones. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-124` | VMS shall allow Admin to configure default walk-in pass duration. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-125` | VMS shall version access policies. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-126` | VMS shall require policy publication before access policy changes take effect. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-127` | VMS shall consume only published access policies for runtime validations. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-128` | VMS shall create new policy versions when access policies are modified. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-129` | VMS shall not apply access policy modifications retroactively to active visits. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-130` | VMS shall allow Admin to trigger emergency muster. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-131` | VMS shall allow Security Personnel to trigger emergency muster. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-132` | VMS shall generate a real-time list of all on-site visitors during emergency muster. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-133` | VMS shall include visitor name, phone, and email in the emergency on-site visitor list. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-134` | VMS shall include last-seen zone and timestamp in the emergency on-site visitor list. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-135` | VMS shall include Host information in the emergency on-site visitor list. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-136` | VMS shall allow roll-call updates of visitor status during emergency muster. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-137` | VMS shall generate a post-event report after emergency muster. | `modules/vms/selectors/reports.py` | Active |
| `VMS-AFR-138` | VMS shall send automated SMS or app alerts to visitors during emergency muster. | `modules/vms/services/security.py` | Partial (muster flow has no SMS/app provider) |
| `VMS-AFR-139` | VMS shall include assembly instructions in emergency alerts sent to visitors. | `modules/vms/services/security.py` | Partial (no alert delivery channel is configured) |
| `VMS-AFR-140` | VMS shall use a cached roster for emergency muster if connectivity fails. | `modules/vms/services/security.py` | Partial (roster is database-backed; offline cache not implemented) |
| `VMS-AFR-141` | VMS shall reconcile cached emergency roster information when connectivity is restored. | `modules/vms/services/security.py` | Partial (offline muster reconciliation is not implemented) |
| `VMS-AFR-142` | VMS shall allow Admin to generate visitor volumes and trends. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-143` | VMS shall allow Admin to generate peak hours and hourly distribution. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-144` | VMS shall allow Admin to generate frequent visitors. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-145` | VMS shall allow Admin to generate denial statistics. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-146` | VMS shall allow Admin to generate SLA compliance based on approval times. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-147` | VMS shall allow Admin to generate daily summary of check-ins, check-outs, and requests. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-148` | VMS shall allow Admin to generate timestamped audit trail logs by visitor or date range. | `modules/vms/models/visits.py; modules/vms/api/views.py` | Active |
| `VMS-AFR-149` | VMS shall allow Admin to generate zone access statistics. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-150` | VMS shall allow Admin to generate blacklist hit reports. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-151` | VMS shall export supported reports in CSV format. | `modules/vms/selectors/reports.py` | Active |
| `VMS-AFR-152` | VMS shall export supported reports in PDF format. | `modules/vms/selectors/reports.py` | Active |
| `VMS-AFR-153` | VMS shall provide anonymized report views for privacy compliance. | `modules/vms/selectors/reports.py` | Active |
| `VMS-AFR-154` | VMS shall allow Admin to upload attendee lists for seminars, drives, or events. | `modules/vms/api/views.py; CSV accepts only existing visit_id references` | Partial |
| `VMS-AFR-155` | VMS shall generate passes for uploaded event attendee lists. | `modules/vms/services/configuration.py; assigns existing passes rather than creating attendee visits` | Partial |
| `VMS-AFR-156` | VMS shall distribute generated event passes to attendees. | `modules/vms/services/scheduled.py; the existing approval pass mail is not reissued by bulk assignment` | Partial |
| `VMS-AFR-157` | VMS shall support pre-assigned slots for event visitor passes. | `modules/vms/services/configuration.py; uses each assigned visit window as its slot` | Partial |
| `VMS-AFR-158` | VMS shall support zone permissions for event visitor passes. | `modules/vms/services/configuration.py; enforces assigned zones as a subset of event zones` | Active |
| `VMS-AFR-159` | VMS shall support event-specific validity for event visitor passes. | `modules/vms/services/configuration.py; requires visit validity to fit the event window` | Active |
| `VMS-AFR-160` | VMS shall support fast-lane QR scanning for high-throughput event entry. | `modules/vms/api/views.py; exposes fast-lane control but uses the standard QR credential validation path` | Partial |
| `VMS-AFR-161` | VMS shall provide live dashboards for event attendance. | `modules/vms/api/views.py; current assigned and on-site counts` | Active |
| `VMS-AFR-162` | VMS shall provide live dashboards for event entry throughput. | `modules/vms/api/views.py; total and rolling one-minute entry counts` | Active |
| `VMS-AFR-163` | VMS shall support walk-in lane rate-limit controls for event overflow handling. | `modules/vms/services/visits.py; event overflow and rate caps gate entry` | Active |
| `VMS-AFR-164` | VMS shall trigger notifications for visit request submission. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-165` | VMS shall trigger notifications for Host approval decision. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-166` | VMS shall trigger notifications for Host rejection decision. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-167` | VMS shall trigger notifications for pass generation and delivery. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-168` | VMS shall trigger notifications for visitor check-in confirmation to Host. | `modules/vms/services/visits.py` | Active |
| `VMS-AFR-169` | VMS shall trigger notifications for visitor check-out notification. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-170` | VMS shall trigger notifications for approval timeout warnings and reminders. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-171` | VMS shall trigger notifications for emergency muster alerts. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-172` | VMS shall trigger notifications for zone access violations. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-173` | VMS shall trigger notifications for blacklist match alerts. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-174` | VMS shall send notifications through system-generated email where configured. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-175` | VMS shall send notifications through system-generated SMS where configured. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Partial (no SMS provider contract is available) |
| `VMS-AFR-176` | VMS shall send notifications through in-app push where configured. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Partial (no push provider contract is available) |
| `VMS-AFR-177` | VMS shall allow Super Admin to assign Admin roles for specific zones or campus-wide scope. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-178` | VMS shall allow Super Admin to reassign Admin roles for specific zones or campus-wide scope. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-179` | VMS shall allow Super Admin to assign Security Personnel roles for specific gates or zones. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-180` | VMS shall allow Super Admin to reassign Security Personnel roles for specific gates or zones. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-181` | VMS shall enforce time-bound role assignments. | `modules/vms/services/roles.py; AuditEvent` | Active |
| `VMS-AFR-182` | VMS shall make role reassignment effective immediately. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-183` | VMS shall route pending requests to newly assigned personnel after reassignment. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-184` | VMS shall represent the hierarchy Super Admin > Admin > Security Personnel for VMS role governance. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-185` | VMS shall treat the Host role as implicit for Faculty and Staff users imported from the institutional user directory. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-186` | VMS shall require every visitor registration to include a valid government-issued identity document. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-187` | VMS shall accept Passport, National ID, Driver's License, or Other as supported identity document type values. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-188` | VMS shall perform blacklist matching case-insensitively. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Needs Clarification |
| `VMS-AFR-189` | VMS shall handle name variations where possible during blacklist matching. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Needs Clarification |
| `VMS-AFR-190` | VMS shall deny entry outside the pass valid-from and valid-until timestamps. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-191` | VMS shall deny unauthorized zone access attempts. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-192` | VMS shall log unauthorized zone access attempts. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-193` | VMS shall prevent visit duration from exceeding the policy-defined maximum duration, with the default treated as 8 hours. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-194` | VMS shall require Admin approval for extensions beyond maximum visit duration. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-195` | VMS shall allow pre-authorized visits to skip the individual approval workflow. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-196` | VMS shall allow Super Admin to grant VIP status that permits policy overrides. | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-AFR-197` | VMS shall allow VIP visits to bypass standard approval and zone restrictions when VIP override applies. | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-AFR-198` | VMS shall send approval reminder notifications at 12 hours for pending requests. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Needs Clarification |
| `VMS-AFR-199` | VMS shall send approval reminder notifications at 20 hours for pending requests. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Needs Clarification |
| `VMS-AFR-200` | VMS shall mark expired pending requests as Expired. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-201` | VMS shall notify the Visitor when a pending request expires. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-202` | VMS shall require pre-registration to be submitted at least 2 hours before the scheduled visit. | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-AFR-203` | VMS shall require Admin approval for same-day urgent visit requests. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-204` | VMS shall ensure draft access policy changes do not affect live system behavior. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-205` | VMS shall ensure unpublished blacklist registry changes do not affect live system behavior. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-206` | VMS shall store visitor identity, contact, document, photo, and organization information for registration and identification. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-207` | VMS shall maintain Host profile information linked to institutional user accounts for visit approval and lookup. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-208` | VMS shall maintain visit request records with visitor, host, purpose, schedule, requested zones, status, submission, approval, notes, and rejection reason information. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-209` | VMS shall restrict visit request states to PENDING, PENDING_HOST_APPROVAL, APPROVED, REJECTED, CANCELLED, and EXPIRED where those states are used. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Needs Clarification |
| `VMS-AFR-210` | VMS shall maintain visitor pass records containing pass credentials, validity, active status, issuer, pass type, and permitted zone information. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-211` | VMS shall restrict pass types to PRE_REGISTERED, WALK_IN, and VIP. | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-AFR-212` | VMS shall maintain visit logs for CHECK_IN, CHECK_OUT, ZONE_ACCESS, and ACCESS_DENIED events. | `modules/vms/services/visits.py; modules/vms/services/security.py` | Active |
| `VMS-AFR-213` | VMS shall maintain active campus zone records with name, description, and access-level information for access restriction validation. | `modules/vms/services/security.py` | Active |
| `VMS-AFR-214` | VMS shall maintain active blacklist records with identity, contact, reason, severity, owner, and expiry information for runtime blacklist checks. | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-AFR-215` | VMS shall maintain access policy records with version, publication status, visiting hours, maximum duration, and restricted zone information. | `modules/vms/services/policies.py` | Active |
| `VMS-AFR-216` | VMS shall maintain audit log records containing actor, action, message, metadata, and timestamp for compliance and review. | `modules/vms/models/visits.py; modules/vms/api/views.py` | Active |
| `VMS-AFR-217` | VMS shall integrate with the Campus ID System for host lookup. | `modules/directory/contracts.py; Campus ID connector is not configured` | Partial |
| `VMS-AFR-218` | VMS shall integrate with the Campus ID System for host verification. | `modules/directory/contracts.py; directory record verification` | Partial |
| `VMS-AFR-219` | VMS shall import Faculty and Staff user information from the central user directory for Host recognition. | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-AFR-220` | VMS shall trigger notifications through the institutional email system where email delivery is configured. | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-AFR-221` | VMS shall trigger SMS alerts for critical notifications such as pass delivery and emergency alerts. | `notification connector not present in this checkout` | Not implemented |
| `VMS-AFR-222` | VMS shall integrate with door readers and turnstiles for zone access control. | `Access Control connector contract is not present in this checkout` | Not implemented |
| `VMS-AFR-223` | VMS shall provide real-time pass validation at physical checkpoints through the access-control integration. | `VMS validates its local pass API; physical reader integration is not present` | Partial |
| `VMS-AFR-224` | VMS shall coordinate with Event Management only for bulk visitor handling for campus events. | `modules/vms/services/configuration.py; local CSV guest assignment only` | Partial |
| `VMS-AFR-225` | VMS shall coordinate with Hostel Management only for visitor logging for hostel areas. | `Hostel connector contract is not present in this checkout` | Not implemented |
| `VMS-AFR-226` | VMS shall not treat Campus ID System, Email/SMS Gateway, Access Control System, Event Management, or Hostel Management as internal VMS actors. | `modules/vms/services/configuration.py; bulk operation not implemented` | Scope Constraint |
| `VMS-BR-037` | Mandatory Pre-registration Validation | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-038` | Duplicate Visit Request Check | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-BR-049` | Walk-in Contingency Approval Authorization | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-050` | Walk-in Contingency Approval SLA | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-051` | Blacklist Registration Rejection | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-052` | Host Approval Requirement | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-BR-053` | Walk-in Pass Duration | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-062` | Pending Approval Timeout | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-BR-073` | Early Pass/Visit Termination Authorization | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-077` | Active Pass Gate Rule | `modules/vms/services/visits.py` | Active |
| `VMS-BR-082` | Gate Validation Failure Rule | `modules/vms/services/visits.py` | Active |
| `VMS-BR-085` | Manual Gate Override Authorization | `modules/vms/services/visits.py` | Active |
| `VMS-BR-096` | Temporary Zone Elevation Time Box | `modules/vms/services/security.py` | Active |
| `VMS-BR-101` | Automatic Checkout Trigger | `modules/vms/services/visits.py` | Active |
| `VMS-BR-105` | Visit Completion Rule | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-112` | Blacklist Runtime Checkpoints | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-116` | Blacklist Entry Denial | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-117` | Blacklist Match Alert | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-118` | Temporary Safe-list Scope | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-119` | Temporary Safe-list Expiry | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-120` | Published Blacklist Runtime Source | `modules/vms/services/policies.py; modules/vms/domain/validation.py` | Active |
| `VMS-BR-125` | Access Policy Versioning | `modules/vms/services/policies.py` | Active |
| `VMS-BR-126` | Access Policy Publication | `modules/vms/services/policies.py` | Active |
| `VMS-BR-127` | Published Access Policy Runtime Source | `modules/vms/services/policies.py` | Active |
| `VMS-BR-128` | Policy Modification Creates New Version | `modules/vms/services/policies.py` | Active |
| `VMS-BR-129` | Policy Non-retroactivity | `modules/vms/services/policies.py` | Active |
| `VMS-BR-130` | Emergency Muster Trigger Authorization | `modules/vms/services/security.py` | Active |
| `VMS-BR-174` | Notification Channel Configuration | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-BR-181` | Time-bound VMS Role Assignment | `modules/vms/services/roles.py; AuditEvent` | Active |
| `VMS-BR-182` | Immediate Role Reassignment | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-183` | Pending Work Handoff on Reassignment | `modules/vms/services/roles.py; AuditEvent` | Active |
| `VMS-BR-184` | VMS Role Hierarchy | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-185` | Implicit Host Role | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-BR-186` | Valid Identity Document Requirement | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-187` | Supported Identity Document Types | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-190` | Pass Validity Window | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-191` | Unauthorized Zone Access Denial | `modules/vms/services/security.py` | Active |
| `VMS-BR-192` | Unauthorized Zone Access Logging | `modules/vms/services/security.py` | Active |
| `VMS-BR-193` | Maximum Visit Duration | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-194` | Extension Approval | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-195` | Pre-authorization Approval Bypass | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py` | Active |
| `VMS-BR-196` | VIP Override Authorization | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-BR-197` | VIP Override Effect | `modules/vms/services/configuration.py; AuditEvent` | Active |
| `VMS-BR-200` | Expired Request State | `modules/vms/services/scheduled.py; modules/vms/tasks.py` | Active |
| `VMS-BR-202` | Advance Pre-registration Window | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-203` | Same-day Urgent Visit Exception | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-BR-211` | Pass Type Domain | `modules/vms/domain/validation.py; modules/vms/services/visits.py` | Active |
| `VMS-UC-001` | Configure VMS Roles | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-002` | Configure VMS Integration Boundaries | `modules/vms/services/configuration.py; AuditEvent; modules/vms/api/views.py` | Active |
| `VMS-UC-003` | Manage VIP Visitor Permissions | `modules/vms/services/configuration.py; AuditEvent; modules/vms/api/views.py` | Active |
| `VMS-UC-004` | Review Audit Trails for Security | `modules/vms/models/visits.py; modules/vms/api/views.py; modules/vms/api/views.py` | Active |
| `VMS-UC-005` | Manage Access Policies | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-006` | Manage Blacklist/Watchlist and Safe-list Registry | `modules/vms/services/policies.py; modules/vms/domain/validation.py; modules/vms/api/views.py` | Active |
| `VMS-UC-007` | Generate Visitor Reports and Analytics | `modules/vms/selectors/reports.py; modules/vms/api/views.py` | Active |
| `VMS-UC-008` | Manage Bulk Visitor Lists and Approvals | `modules/vms/services/configuration.py; approved-visit assignment only; modules/vms/api/views.py` | Partial |
| `VMS-UC-009` | Coordinate Special-Event Visitor Handling | `modules/vms/services/configuration.py; approved-visit assignment only; modules/vms/api/views.py` | Partial |
| `VMS-UC-010` | Pre-register Visit | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-011` | Track Visit Request Status and History | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-012` | Access Digital Pass | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-013` | Decide Visit Request | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-014` | Pre-authorize Recurring Visitor | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-015` | View Visitor Arrival Updates | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-016` | Terminate Visitor Visit Early | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-017` | Register Walk-in Visitor at Gate | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-018` | Validate Visitor Pass at Gate | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-019` | Process Manual Gate Override | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-020` | Record Manual Visit Log | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-021` | Check Out Visitor at Gate | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-022` | Monitor Live Visitor Dashboard | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-023` | Validate Zone Access | `modules/vms/services/security.py; modules/vms/api/views.py` | Active |
| `VMS-UC-024` | Grant Temporary Zone Elevation | `modules/vms/services/security.py; modules/vms/api/views.py` | Active |
| `VMS-UC-025` | Handle Zone Violation Alert | `modules/vms/services/security.py; modules/vms/api/views.py` | Active |
| `VMS-UC-026` | Trigger Emergency Muster | `modules/vms/services/security.py; modules/vms/api/views.py` | Active |
| `VMS-UC-027` | Perform Emergency Roll-call | `modules/vms/services/security.py; modules/vms/api/views.py` | Active |
| `VMS-UC-028` | Process Gate Entry in Offline Mode | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-030` | View Visitor Notifications | `modules/vms/services/scheduled.py; modules/vms/tasks.py; modules/vms/api/views.py` | Active |
| `VMS-UC-031` | Self-Checkout Visit | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-032` | Trigger Emergency Muster | `modules/vms/services/security.py; modules/vms/api/views.py` | Active |
| `VMS-UC-033` | Decide Walk-in Contingency Approval | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-034` | Decide Visit Extension | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-035` | Decide Same-Day Urgent Visit Exception | `modules/vms/domain/validation.py; modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-036` | Terminate Visitor Visit Early | `modules/vms/services/visits.py; modules/vms/domain/state_machine.py; modules/vms/api/views.py` | Active |
| `VMS-UC-037` | Expire Pending Visit Request | `modules/vms/services/scheduled.py; modules/vms/tasks.py; modules/vms/api/views.py` | Active |
| `VMS-UC-038` | Automatically Check Out Visit | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-039` | Reconcile Cached Offline Gate Entries | `modules/vms/services/visits.py; modules/vms/api/views.py` | Active |
| `VMS-UC-040` | Send Pending Approval Reminder | `modules/vms/services/scheduled.py; modules/vms/tasks.py; modules/vms/api/views.py` | Active |

## Domain model and invariants

- `VisitorProfile`, `VisitorDocument`, `VisitorAccessCredential`, `VisitRequest`, `VisitPass`, `VisitLog`, `AuditEvent`, `NotificationOutbox`, `AccessPolicyVersion`, `RegistryVersion`, `BlacklistEntry`, `SafeListEntry`, `VipPermission`, `PreAuthorization`, `VmsRoleAssignment`, `IntegrationSetting`, `EventRecord`, `EventGuestBatch`, `EventGuestBatchRow`, `GateAttempt`, `ZoneAccessEvent`, `ZoneElevation`, `ZoneAlert`, `EmergencyMuster`, `MusterRollCall`, and `OfflineGateEvent` are VMS-owned entities.
- External people use integer `host_user_id` only; within-module aggregates use FKs. Visitor document numbers are never stored in plaintext; a keyed fingerprint supports duplicate/registry comparisons, with only a masked suffix retained for display. Visitor and pass credentials are signed, expiring tokens backed by random nonces; outbox rows store references and the delivery task creates bearer tokens only in memory.
- Request transitions are declarative and serialized with `select_for_update`; terminal requests cannot be reactivated. Pass status, request status, and physical presence are separate facts. Gate entry/exit events are append-only; corrections are additional events.
- Database constraints enforce visitor identity uniqueness, policy/registry version uniqueness, gate/offline idempotency keys, one pass per visit, and valid time intervals. Services do not expose edits to published policy/registry versions.

## State machine

`NOT_SUBMITTED -> PENDING_HOST_APPROVAL | PENDING_ADMIN_CONTINGENCY | PENDING_URGENT_REVIEW`; pending requests transition to `APPROVED`, `REJECTED`, or `EXPIRED`; authorization creates an active pass with type `PRE_REGISTERED`, `WALK_IN`, or `VIP`; successful entry creates `ON_SITE`; recorded/manual or automatic checkout creates `COMPLETED`. Event guest assignment does not add a pass type. Active pass/visit may transition to `TERMINATED`. Zone violations and overrides are separate records and never create implicit entry. `CANCELLED` remains a recognized persisted state with no actor transition because the specs define no cancellation actor flow. Every transition is actor-checked, policy-checked, audited, and committed atomically.

## Permission design

Permission codes use the closed IAM verb set and `vms.<singular_resource>.<verb>`. Public visitor access is token-scoped and does not use institutional permissions. `Host` gets only own-request decisions, pre-authorizations, updates, and history. Admin, Security Personnel, and Super Admin get distinct permissions for policy/registry/event/override, gate/zone/muster operations, and role/integration/VIP/audit administration. System-only permissions cover expiry, auto-checkout, offline reconciliation, reminders, and notification delivery. `ROLE_GRANTS` is keyed by the exact role names approved above; role grants do not widen a selector's data scope. Every client nav item names a required permission and is mirrored by a guarded route.

## Endpoint plan

All routes are mounted at `/api/v1/vms/`. JSON writes accept an idempotency key where retries can duplicate state. Public pre-registration and gate walk-in accept multipart identity documents. Admin event guest imports accept a bounded CSV with a single `visit_id` column; only previously approved visits with clean documents and live passes can be assigned. Event activation/completion, control updates, guest import outcomes, attendance, and event entry rate/occupancy controls are available to the defined Admin/Security roles. Other endpoints remain grouped as `public/hosts`, `visitor/requests`, `visits`, `gate`, `security`, and `admin`. Each endpoint has module and permission gates, or an explicitly scoped visitor-token authenticator.

## Contracts and external systems

VMS reads host display/email data through the existing plural `directory.get_users(user_ids)` contract. VMS will not add IAM endpoints or cross-module model imports. No Event Management, Hostel Management, access-control, campus ID, or push/SMS connector currently exists in this checkout; VMS records integration settings/events and fails closed when a required online validation source is unavailable. Email notification delivery uses the existing Django mail configuration through a VMS transactional outbox.

## Scheduled work

Celery beat runs bounded sweeps for pending approval expiry, configured reminders, pass expiry, visit auto-checkout, offline-event reconciliation, pending document scans, and notification outbox delivery. The visit and registry services recheck policy windows when accepting operations. Notification delivery uses retries with backoff and clears bearer content after successful delivery.

## Implementation status

Implemented in this checkout: initial and additive schema migrations; pre-registration and gate walk-in identity-document upload; private file storage, PDF rewriting, ClamAV scan scheduling, and clean-scan gates for entry/download; host decisions, visitor status credentials, pre-authorization, urgent and contingency review, pass issuance, blacklist checks, check-in/out, offline reconciliation, policy/registry services, role assignments, VIP permissions, event lifecycle/controls/guest-list assignment and event entry caps, zones, muster/roll-call, audit/outbox, reports, scheduled expiry/reminders/auto-checkout/reconciliation/document scanning/email, visitor/host/security pages, and Admin event operations. Visit termination, visitor self-checkout, extension decisions, manual visit logs, and narrowly scoped Admin gate overrides are also implemented.

Production integration boundary: directory and institutional email use existing contracts. Campus ID, Event Management, Hostel Management, Access Control, SMS, and in-app notification connectors are not implemented because this checkout supplies no external API contracts or credentials. Those connections must be scoped with the owning systems before they can be enabled. The event CSV currently references already-approved visit IDs rather than creating new visit identities or overriding Host approval.

Verification is limited to Python syntax compilation, registry/navigation structure, migration-file presence, and `git diff --check`. Django and frontend dependencies are absent here, so migrations, Django deploy checks, and client builds have not run. The independent Student 2 FR/UC/BR/WF suite and their acceptance review remain outstanding; no score, review, deployment, or PR is claimed.

## Open/approved assumptions

The user's instruction assumes Student 2 approved the following conservative resolutions: exact normalized matching without fuzzy name matching; no override for active blacklist denial; default reminder offsets of 12/20 hours; no cancellation transition despite retaining the `CANCELLED` enum; visitor email link authentication with scoped, expiring access credentials; role labels as designation names; and docs number 09. The implementation will not claim that the separate Student 2 review, spec-derived tests, 10/10 score, complete production integration setup, or PR has occurred.
