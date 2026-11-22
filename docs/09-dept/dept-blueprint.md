# DEPT module blueprint — approved to proceed by user

**Status:** Blueprint decisions recorded by the implementation owner under the user’s direction to proceed without Student 2 intervention. Student 2 approval gate waived by user. Implementation is authorized to proceed; this remains subject to the repository architecture and local verification.

**Module:** Department (DEPT)
**Repository code / URL segment:** `dept`
**Specification set:** v1.2 student baseline, 2026-08-30
**Environment:** `module-only`
**Documentation folder:** `docs/09-dept/`
**Assignment gate:** The user explicitly directed that Student 2 will not intervene and authorized the implementation owner to choose the best available decisions. This waives the Student 2 review gate for this run; it does not waive security, architecture, or verification requirements.

## 1. Phase 0 inventory

### Artefact counts

| Artefact | Count | Notes |
|---|---:|---|
| CFRs | 16 | Active requirements. |
| AFRs | 51 | Active requirements. |
| Use cases | 20 | Active UCs. |
| Business rules | 22 | Active BRs. |
| Basis workflows | 8 | Active. |
| Composite workflows | 4 | Active. |

Source: the six DEPT baseline documents and workbook supplied in the assignment. The workbook summary reports the counts above. Its detailed mapping columns are empty for CFR/AFR, UC, BR and WF mappings; coverage must be derived from the detailed specifications, not presumed from the summary.

### Retired and reserved identifiers

- `FR-DEPT-032` and `FR-DEPT-033` are historical/retired; they have no active AFR. The critical timetable-approval interpretation was removed. Do not implement a timetable approval path under these IDs.
- `UC-DEPT-013` is retired as a generic System notification UC. Notification behavior is specified through active requirement IDs and the triggering use cases.
- `UC-DEPT-021` is reserved/draft-only for critical timetable approval and is not an active UC. Its identifier must not be reused.
- `DEPT-WF-103` is a legacy workflow mapping to `CW-DEPT-01`, not a separate current workflow.
- `BR-DEPT-014` (generic notification dispatch) is retired; its behavior is represented in `FR/AFR-DEPT-041..046` and triggering UCs.
- `BR-DEPT-020` is absent from the active list; the baseline does not state that this identifier is retired. No rule or retirement status is inferred for it.

### Actors found in the specification set

HOD, Dept_Admin, Faculty, Student, institute administrator/central authority, and System/event actor. The module uses the exact role keys `HOD` and `Dept_Admin`, faculty/student basic kinds, and the existing IAM operator-admin pool for central appointment maintenance. An active IAM appointment is required for office-role access.

### Cross-document consistency and implementation constraints

No direct contradictory behavior between the source documents was established during the review. `BR-DEPT-010` mentions not saving an overlapping timetable “or advancing it for approval,” while the current requirement/use-case baseline removes a separate timetable-approval path. This implementation enforces overlap at save time and does not restore an approval flow.

The source leaves profile fields, feedback identity, overlap semantics, notification channels, concurrent stock behavior, and course enrollment data unspecified. Explicit conservative defaults are recorded in section 4.

## 2. Phase 1 architecture and boundary assessment

### Bounded context

DEPT is one bounded context: departmental announcements, inventory requests/issuance, feedback, timetable/resources, department details, profile presentation, notifications, and role transitions. It owns its business records; it must not own identity, designation, or authorization tables.

### Existing contracts

- `modules/directory/contracts.py` exposes batched user projections (`get_users`) and directory searches. It does not expose the teaching/course relationship needed to restrict Faculty profile visibility to students in their courses.
- `fusion_auth.Principal` exposes identity, active designation, roles, permissions, modules, and navigation. It has no department scope or designation effective dates.
- The IAM API in the supplied IAM checkout exposes session, directory, academic standing/directory/filter projections. No endpoint was found for department role assignments, department scopes, or effective-dated assignments.
- Do not connect DEPT directly to `fusionlab` or add an IAM client method for a nonexistent IAM endpoint.

### Architecture gaps and integration decisions

1. **Department-scoped roles are not expressible in current auth context.** DEPT requires HOD and Dept_Admin authority scoped to a department, while the active `Principal` has no scope. A permission grant alone would be institute-wide. Adding local scope tables or inferring scope from an editable department label would create an unauthorized second source of truth.
2. **Effective-dated, immediately effective assignments are not expressible.** The IAM projection of designations contains a user and designation only. DEPT requires central authority to assign/reassign time-bound HOD/Dept_Admin roles, revoke/grant at the effective instant, and maintain exactly one active office-holder of each kind per department. No public IAM assignment contract supports that lifecycle.
3. **Some data dependencies lack an exposed contract.** Course-to-student membership is needed for the specified profile visibility; a department entity/identifier and authoritative membership relation are needed to scope records. Existing `UserDTO.department` is a display string and not a safe authorization key. No contract should be guessed or locally duplicated.
4. **Inventory concurrency policy is unresolved.** The problem statement validates stock when a request is made and does not reserve stock or revalidate at issuance. Multiple approved requests can therefore exceed available stock unless another stated rule exists. The module prompt forbids choosing an unstated policy.
5. **Student profile/feedback privacy decisions are not sufficiently defined for safe projection.** Visibility and confidentiality are described at a high level, but field-level allowlists and feedback identity exposure/anonymity behavior are not settled.

The user authorized the implementation owner to resolve these gaps without Student 2 intervention. The resulting decisions are documented in section 4 and implemented through a real IAM contract change. Course enrollment remains unavailable, so the profile policy is deliberately limited rather than inferring course access.

## 3. Phase 2 design sections — decisions recorded

The implementation decisions below resolve the underspecified policies conservatively. Any IAM surface not present in the current service must be implemented in the IAM repository and integrated by a real contract; no nonexistent endpoint will be faked.

- **(a) Traceability:** the supplied workbook mappings are blank; see the source artefact inventory above and implementation coverage in the API, service, and model layers. Detailed per-ID remapping remains a delivery item.
- **(b) Domain model and invariants:** implemented in `modules/dept/models/` and its initial migration.
- **(c) State machines:** stock, feedback, department changes, and timetable conflict behavior are implemented in the domain/service layer; IAM appointments are date-bounded.
- **(d) Permissions and role grants:** defined in `modules/dept/registry.py`; endpoint guards require both module access and resource permission.
- **(e) Endpoints and navigation:** mounted under `/api/v1/dept/`; the client module is registered at `/dept`.
- **(f) Inter-module contract:** the IAM repository carries office assignments in `/me` and exposes operator-managed appointments. Directory identity stays read-only; course enrollment remains an explicit limitation.
- **(g) Scheduled work:** notification dispatch runs on the existing Celery notifications queue; appointment activity is evaluated by IAM on session resolution.

## 4. Implementation decisions recorded

Chosen defaults under the user’s instruction to exercise judgment (2026-11-21). These are explicit policy choices where the baseline is silent:

1. **Role authority and scope:** IAM remains the sole authority for office appointments. Add an IAM appointment record with `department_code`, role (`HOD` or `Dept_Admin`), user id, start and end dates, and creation audit. Expose active appointments in `/me` and provide operator-only appointment maintenance endpoints. DEPT keeps no shadow authorization table. Effective dates are evaluated in IAM; appointment transitions are reflected on each session refresh. The IAM change is a separate required integration in `Fusion_System_Administrator`.
2. **Designation catalogue:** Use the specification’s canonical labels `HOD` and `Dept_Admin` as IAM appointment role codes and manifest grant keys. The central Institute Admin is represented by the existing IAM operator-admin pool, not a new ERP designation. Do not create an ERP designation implicitly.
3. **Department and teaching scopes:** Use normalized department codes in the IAM appointment contract; names/labels are display-only. Until an authoritative course-enrollment contract is available, student profile visibility is limited to the same department and faculty profile visibility is limited to public/basic fields; course-specific student access is not inferred from names or department labels. The IAM role appointment endpoints are the source of office scopes.
4. **Stock race behavior:** Validate available quantity on request as specified, do not reserve on request, and atomically reserve quantity when HOD approves. Issuance converts the reservation to an immutable issue movement; rejection/revocation releases any reservation. This prevents concurrent approvals from promising the same units while preserving the request-time eligibility check. The added approval-time reservation is a documented conservative interpretation because the source does not define concurrent oversubscription.
5. **Profile privacy:** Return only display name, kind, programme, discipline, batch year, and module-owned professional profile fields. Exclude email, phone, address, personal identifiers, academic marks, resume link, and other sensitive data from peer/profile views. A directory identity is read-only; Dept_Admin can maintain only DEPT-owned profile metadata for users in their assigned department.
6. **Feedback confidentiality:** Feedback is authenticated and confidential, not anonymous. Only the submitter, assigned Dept_Admin, and assigned HOD can read it; identity is visible only to those authorized reviewers and the submitter. No attachments in v1.2; feedback becomes immutable after terminal resolution except for audit metadata.
7. **Timetable overlap wording:** Do not restore the retired approval workflow. Validate and reject conflicting timetable saves. A slot conflicts where the same resource/room or same cohort has overlapping half-open intervals on the same day; exact data absent means the conflict check is based on the timetable’s explicit cohort and resource keys.
8. **Notification channels:** Persist an in-app notification/outbox event for every specified trigger and deliver it asynchronously. Email is best-effort only when an address exists; delivery failure does not roll back the originating business transaction. No channel selection policy is implied for users.

## 5. Blueprint implementation outline

### Domain and state

- `Department`: canonical code and display details, keyed by a stable code supplied in DEPT configuration; no user-name-to-department inference.
- `Announcement`: department, author id, audience filters, content, publication state and timestamps.
- `InventoryItem`: department, label, on-hand quantity, reserved quantity, active flag, and audit metadata. Enforce `on_hand >= 0`, `reserved >= 0`, and `reserved <= on_hand` in the database.
- `StockMovement`: append-only insertion, reservation, release and issuance movements, actor id, request id where relevant, quantity and timestamp. No update/delete service.
- `StockRequest`: requester id, item id, quantity, status and decision/issue actor ids. Declarative transitions: `Pending -> Approved | Rejected`; `Approved -> Issued | Cancelled`; terminal states immutable. Row-lock item/request in one transaction.
- `Feedback`: submitter id, category, text, status, reviewer ids, resolution and timestamps. `New -> UnderReview -> Resolved | Closed`; no terminal transition. HOD can resolve only after Dept_Admin initial review.
- `UserProfile`: plain IAM user id and department code plus DEPT-owned non-sensitive profile fields. Never duplicates or writes IAM identity fields.
- `TimetableSlot`: department, cohort key, resource key, weekday and half-open start/end. Reject overlapping slots for same cohort or resource atomically.
- `LabResource`: department, metadata and active state.
- `DepartmentDetail` / `DepartmentDetailProposal`: general data changes effective immediately; official fields create a pending proposal; approval applies it and rejection retains current values. Headship is read from active IAM HOD appointment.
- IAM-owned `DepartmentAppointment` is the only role assignment source; DEPT uses the appointment scope carried in the authenticated session.
- `Notification` / outbox record: recipient user id, event type, entity reference, delivery state and timestamps. No cross-module foreign keys.

### Scheduled work

Celery task runs every minute to deliver queued notification email and retry transient failures with bounded exponential backoff. IAM session evaluation checks appointment effective dates at request time; no DEPT beat task is needed to grant/revoke permissions, avoiding stale access if a scheduler is down.

### Current contract dependency

IAM must expose department appointments, their role, and active interval in `/me`, and an operator-admin write API to create/correct appointments. `IamClient`/`FakeIam` and `Principal` must carry these claims. The DEPT API must fail closed when appointment data is missing. This is a real IAM implementation, not a fake client method.

### Navigation handoff (`Fusion-client`, module-only)

`{ id: "dept", label: "Department", icon: "Buildings", to: "/dept", section: "Modules" }`.

### Open limitations recorded

- The IAM appointment API and session claims are implemented in the sibling `Fusion_System_Administrator` checkout and require a coordinated deployment/release with A9.
- The current directory has no course enrollment relationship; course-specific visibility cannot safely be implemented until IAM adds that projection. V1.2 will enforce the conservative same-department and least-privilege profile policy above.
- The exact cohort/resource overlap interpretation and profile field choices are documented decisions because the source does not specify them.
- Student 2’s assignment review was explicitly waived by the user; this must be mentioned in the quality report, not misrepresented as received approval.
- Full PostgreSQL integration verification remains necessary. Local DEPT pytest coverage uses SQLite and skips one JSON-array containment test because the production PostgreSQL lookup is not supported by SQLite.
- Client typecheck passes, but Vite/Vitest/esbuild fail to read the config in this restricted Windows workspace (`Access is denied` while traversing to the filesystem root); the production build and client test suite are not yet verified.

## 6. Work boundary

Blueprint decisions are recorded above. Application implementation now proceeds under the user’s direction. The cross-repository IAM contract is required; no missing IAM API will be simulated. The waived Student 2 gate will be transparently recorded in the quality report.
