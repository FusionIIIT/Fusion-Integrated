# Department module blueprint

Module code `department`. Documentation `docs/09-department/`. Environment `module-only`. Source Department (DEPT) student baseline v1.2.

## Traceability

The enforcement points below describe the planned module. The first increment implements the announcement read contract. The external dependencies listed below remain open.

| ID | Obligation | Layer | Enforcement point |
| --- | --- | --- | --- |
| CFR-DEPT-001 | Publish Targeted Department Announcements | Services | Announcement publication and filtered notifications |
| CFR-DEPT-002 | Deliver Relevant Announcements | Selectors | Announcement visibility |
| CFR-DEPT-003 | Maintain Active Announcements | Services | HOD announcement maintenance |
| CFR-DEPT-004 | Maintain Inventory Records and Audit Trail | Services and models | Inventory insertion and movement log |
| CFR-DEPT-005 | Process Stock Requests to Final Outcome | Services and domain | Stock request and issuance lifecycle |
| CFR-DEPT-006 | Provide Faculty Issued-Stock History | Selectors | Faculty issued-stock history |
| CFR-DEPT-007 | Submit Confidential Feedback | Services and selectors | Confidential feedback submission |
| CFR-DEPT-008 | Review and Resolve Feedback | Services and domain | Feedback review and disposition |
| CFR-DEPT-009 | Manage Department User Profiles | External contract | Profile write semantics and policy |
| CFR-DEPT-010 | Enforce Department Profile Visibility | External contract | Profile visibility policy and course roster |
| CFR-DEPT-011 | Manage Conflict-Free Timetables | Services and models | Timetable overlap constraints |
| CFR-DEPT-012 | Manage and View Lab Resource Profiles | Services and selectors | Lab resource profiles |
| CFR-DEPT-013 | Provide Student Academic Information | Selectors | Student programme and timetable access |
| CFR-DEPT-014 | Update General Department Information | Services | Allowlisted general details |
| CFR-DEPT-015 | Control Official Department-Detail Changes | Services and domain | Official detail change approval |
| CFR-DEPT-016 | Maintain Department Role Assignments and Effective Access | External contract | IAM role handoff and Headship |
| AFR-DEPT-001 | The system shall allow Faculty, Dept_Admin, and HOD users to create and publish department announcements. | Services | Announcement publication and filtered notifications |
| AFR-DEPT-046 | The system shall notify relevant Students and Faculty when a new announcement is published for their target scope. | Services | Announcement publication and filtered notifications |
| AFR-DEPT-002 | The system shall filter announcement visibility using the viewer's role, program, and academic year against the announcement target scope. | Selectors | Announcement visibility |
| AFR-DEPT-003 | The system shall allow authenticated department users to view announcements that are relevant to them after visibility filtering. | Selectors | Announcement visibility |
| AFR-DEPT-004 | The system shall allow the HOD to edit any active department announcement. | Services | HOD announcement maintenance |
| AFR-DEPT-005 | The system shall allow the HOD to hide any active department announcement. | Services | HOD announcement maintenance |
| AFR-DEPT-006 | The system shall allow the HOD to delete any active department announcement. | Services | HOD announcement maintenance |
| AFR-DEPT-007 | The system shall allow Dept_Admin to insert stock records into the department inventory. | Services and models | Inventory insertion and movement log |
| AFR-DEPT-008 | The system shall maintain the current inventory state and quantity for department stock items. | Services and models | Inventory insertion and movement log |
| AFR-DEPT-014 | The system shall record every stock insertion in an immutable stock-movement log. | Services and models | Inventory insertion and movement log |
| AFR-DEPT-009 | The system shall allow Faculty members to submit requests for department inventory items. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-010 | The system shall validate a requested stock quantity against the current inventory level before accepting the request for approval. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-011 | The system shall allow the HOD to approve or reject a pending Faculty stock request. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-012 | The system shall allow Dept_Admin to issue stock only for a request approved by the HOD. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-013 | The system shall automatically decrement the relevant inventory quantity when approved stock is issued. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-015 | The system shall record every stock issuance in an immutable stock-movement log. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-041 | The system shall send a real-time system notification and/or email to Dept_Admin when a new stock request is submitted. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-042 | The system shall send a real-time system notification and/or email to the HOD when a stock request requires HOD authorization. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-043 | The system shall notify the requesting Faculty member when the stock request reaches the final Issued or Rejected outcome. | Services and domain | Stock request and issuance lifecycle |
| AFR-DEPT-016 | The system shall allow Faculty members to view their relevant issued-stock history. | Selectors | Faculty issued-stock history |
| AFR-DEPT-017 | The system shall allow authenticated Students and Faculty to submit department feedback. | Services and selectors | Confidential feedback submission |
| AFR-DEPT-018 | The system shall protect submitted feedback as confidential information accessible only within authorized feedback-handling scope. | Services and selectors | Confidential feedback submission |
| AFR-DEPT-044 | The system shall notify Dept_Admin when new feedback is submitted. | Services and selectors | Confidential feedback submission |
| AFR-DEPT-019 | The system shall allow Dept_Admin to perform the initial review of newly submitted feedback. | Services and domain | Feedback review and disposition |
| AFR-DEPT-020 | The system shall allow Dept_Admin to categorize feedback during the initial review. | Services and domain | Feedback review and disposition |
| AFR-DEPT-021 | The system shall allow Dept_Admin to close a feedback item considered a simple issue during initial review. | Services and domain | Feedback review and disposition |
| AFR-DEPT-022 | The system shall allow Dept_Admin or HOD to mark feedback as Resolved or Closed. | Services and domain | Feedback review and disposition |
| AFR-DEPT-023 | The system shall allow the HOD to access feedback after initial review for oversight and resolution actions. | Services and domain | Feedback review and disposition |
| AFR-DEPT-045 | The system shall notify the feedback submitter when feedback is marked Resolved or Closed. | Services and domain | Feedback review and disposition |
| AFR-DEPT-024 | The system shall allow Dept_Admin to manage Faculty, Student, and Alumni profile records within the department. | External contract | Profile write semantics and policy |
| AFR-DEPT-025 | The system shall allow Students to view only basic, permitted profile information for peer Students and Faculty. | External contract | Profile visibility policy and course roster |
| AFR-DEPT-026 | The system shall allow Faculty to view detailed profile information for Students in the Faculty member's courses. | External contract | Profile visibility policy and course roster |
| AFR-DEPT-027 | The system shall allow Faculty to view permitted limited-scope profile information for Faculty and Alumni. | External contract | Profile visibility policy and course roster |
| AFR-DEPT-028 | The system shall allow HOD and Dept_Admin to view full department user profiles except sensitive personal data protected by applicable privacy policy. | External contract | Profile visibility policy and course roster |
| AFR-DEPT-029 | The system shall allow Dept_Admin to upload class and lab timetables. | Services and models | Timetable overlap constraints |
| AFR-DEPT-030 | The system shall allow Dept_Admin to modify existing class and lab timetables. | Services and models | Timetable overlap constraints |
| AFR-DEPT-031 | The system shall detect overlapping timetable slots before a timetable is saved and shall block saving when a conflict exists. | Services and models | Timetable overlap constraints |
| AFR-DEPT-034 | The system shall allow Dept_Admin to update department lab equipment and resource profile details. | Services and selectors | Lab resource profiles |
| AFR-DEPT-035 | The system shall allow Faculty to view department lab resource profiles for planning. | Services and selectors | Lab resource profiles |
| AFR-DEPT-036 | The system shall allow Students to view department academic program information. | Selectors | Student programme and timetable access |
| AFR-DEPT-037 | The system shall allow Students to view applicable class/lab timetable information. | Selectors | Student programme and timetable access |
| AFR-DEPT-038 | The system shall allow Dept_Admin to update general department information. | Services | Allowlisted general details |
| AFR-DEPT-039 | The system shall keep proposed official department-detail changes pending until HOD approval and shall not publish them before approval. | Services and domain | Official detail change approval |
| AFR-DEPT-040 | The system shall allow the HOD to approve or reject a pending official department-detail change. | Services and domain | Official detail change approval |
| AFR-DEPT-047 | The system shall allow the central Institute Admin or equivalent authorized authority to assign the Dept_Admin and HOD roles to institute employees for a department. | External contract | IAM role handoff and Headship |
| AFR-DEPT-048 | The system shall maintain a time-bounded validity period for each active HOD and Dept_Admin role assignment. | External contract | IAM role handoff and Headship |
| AFR-DEPT-049 | The system shall immediately revoke Department-role access from the outgoing HOD or Dept_Admin when reassignment or transfer takes effect. | External contract | IAM role handoff and Headship |
| AFR-DEPT-050 | The system shall immediately grant the applicable Department-role access to the incoming HOD or Dept_Admin when reassignment or transfer takes effect. | External contract | IAM role handoff and Headship |
| AFR-DEPT-051 | The system shall enforce that each department has exactly one active HOD role assignment at any given time. | External contract | IAM role handoff and Headship |
| AFR-DEPT-052 | The system shall enforce that each department has exactly one active Dept_Admin role assignment at any given time. | External contract | IAM role handoff and Headship |
| AFR-DEPT-053 | The system shall derive the department's displayed Headship from the current active HOD role assignment maintained by the central Institute Admin or equivalent authority. | External contract | IAM role handoff and Headship |
| UC-DEPT-001 | View Announcements | Selectors | Announcement visibility |
| UC-DEPT-002 | Create Announcement | Services | Announcement publication and filtered notifications |
| UC-DEPT-003 | Manage Active Announcement | Services | HOD announcement maintenance |
| UC-DEPT-004 | Request Stock Item | Services and domain | Stock request and issuance lifecycle |
| UC-DEPT-005 | Approve or Reject Stock Request | Services and domain | Stock request and issuance lifecycle |
| UC-DEPT-006 | Allocate and Issue Stock | Services and domain | Stock request and issuance lifecycle |
| UC-DEPT-007 | Submit Feedback | Services and selectors | Confidential feedback submission |
| UC-DEPT-008 | Initial Review and Disposition of Feedback | Services and domain | Feedback review and disposition |
| UC-DEPT-009 | Manage Timetable | Services and models | Timetable overlap constraints |
| UC-DEPT-010 | Update Department Details | Services | Allowlisted general details |
| UC-DEPT-011 | View Department Resources | Services and selectors | Lab resource profiles |
| UC-DEPT-012 | Approve Official Department Changes | Services and domain | Official detail change approval |
| UC-DEPT-014 | HOD Oversight and Resolution of Feedback | Services and domain | Feedback review and disposition |
| UC-DEPT-015 | View Department User Profiles | External contract | Profile visibility policy and course roster |
| UC-DEPT-016 | Manage Department User Profiles | External contract | Profile write semantics and policy |
| UC-DEPT-017 | Manage Lab Profiles | Services and selectors | Lab resource profiles |
| UC-DEPT-018 | View Academic Program Information and Timetable | Selectors | Student programme and timetable access |
| UC-DEPT-019 | Manage Inventory Records | Services and models | Inventory insertion and movement log |
| UC-DEPT-020 | Maintain Department Role Assignments | External contract | IAM role handoff and Headship |
| UC-DEPT-022 | Apply Effective Department Role Transition | External contract | IAM role handoff and Headship |
| BR-DEPT-001 | Announcement Creation Authority | Services | Announcement publication and filtered notifications |
| BR-DEPT-002 | Announcement Visibility Filtering | Selectors | Announcement visibility |
| BR-DEPT-003 | Announcement Publication Completeness | Services | Announcement publication and filtered notifications |
| BR-DEPT-004 | Announcement Modification Authority | Services | HOD announcement maintenance |
| BR-DEPT-005 | Stock Request Eligibility | Services and domain | Stock request and issuance lifecycle |
| BR-DEPT-006 | HOD Stock Approval Authority | Services and domain | Stock request and issuance lifecycle |
| BR-DEPT-007 | Stock Issuance Control | Services and domain | Stock request and issuance lifecycle |
| BR-DEPT-008 | Feedback Submission Eligibility | Services and selectors | Confidential feedback submission |
| BR-DEPT-009 | Feedback Resolution Authority | Services and domain | Feedback review and disposition |
| BR-DEPT-010 | Timetable Conflict Validation | Services and models | Timetable overlap constraints |
| BR-DEPT-011 | Official Department Data Approval Requirement | Services and domain | Official detail change approval |
| BR-DEPT-012 | Department Resource Visibility | Services and selectors | Lab resource profiles |
| BR-DEPT-013 | HOD Official Update Decision Authority | Services and domain | Official detail change approval |
| BR-DEPT-015 | Stock Availability Validation | Services and domain | Stock request and issuance lifecycle |
| BR-DEPT-016 | Stock Movement Audit Immutability | Services and models | Inventory insertion and movement log |
| BR-DEPT-017 | Feedback Confidentiality and Access | Services and selectors | Confidential feedback submission |
| BR-DEPT-018 | Feedback Initial Review Responsibility | Services and domain | Feedback review and disposition |
| BR-DEPT-019 | Department Profile Visibility Matrix | External contract | Profile visibility policy and course roster |
| BR-DEPT-021 | Central Department Role Assignment Authority | External contract | IAM role handoff and Headship |
| BR-DEPT-022 | Unique Active Department Roles | External contract | IAM role handoff and Headship |
| BR-DEPT-023 | Department Role Tenure | External contract | IAM role handoff and Headship |
| BR-DEPT-024 | Role Reassignment Access Transition | External contract | IAM role handoff and Headship |
| BW-DEPT-01 | Stock Request Approved and Issued | Services and domain | Stock request and issuance lifecycle |
| BW-DEPT-02 | Stock Request Rejected by HOD | Services and domain | Stock request and issuance lifecycle |
| CW-DEPT-01 | Stock Request, Approval and Issuance Lifecycle | Services and domain | Stock request and issuance lifecycle |
| BW-DEPT-03 | Feedback Disposed by Dept_Admin | Services and domain | Feedback review and disposition |
| BW-DEPT-04 | Feedback Disposed with HOD Oversight | Services and domain | Feedback review and disposition |
| CW-DEPT-02 | Feedback Handling Lifecycle | Services and domain | Feedback review and disposition |
| BW-DEPT-05 | Official Department Change Approved | Services and domain | Official detail change approval |
| BW-DEPT-06 | Official Department Change Rejected | Services and domain | Official detail change approval |
| CW-DEPT-03 | Official Department Change Lifecycle | Services and domain | Official detail change approval |
| BW-DEPT-07 | HOD Role Reassignment and Headship Synchronization | External contract | IAM role handoff and Headship |
| BW-DEPT-08 | Dept_Admin Role Reassignment and Access Transition | External contract | IAM role handoff and Headship |
| CW-DEPT-04 | Department Role Reassignment Lifecycle | External contract | IAM role handoff and Headship |

## Domain model

- **Announcement.** Department key from the IAM department projection, authored content, publication timestamp, active/hidden status, and applicable role, programme and cohort-year lists. Target axes combine with AND and values within one axis with OR. An empty axis means explicitly unrestricted within the department. Filter on the current identity and active role, before pagination.
- **Inventory and requests.** Inventory has a department, item identity and nonnegative quantity. Requests reference an item within the module and an integer IAM requester ID, with a strictly positive requested quantity. One atomic transaction locks the item and request during issuance and records an append-only movement and notification event. Constrain the quantity in the database. Request submission checks availability without reserving stock.
- **Feedback.** Department, integer submitter ID, confidential content, categorization, review and disposition timestamps. Initial review and a simple closure may be recorded in one transaction, in that order. Staff queries start with department scoping and per-stage permissions.
- **Timetable and lab.** Department timetable slots use half-open intervals for the applicable term and day. A room, instructor or cohort conflict prevents saving. Lab resource and inventory records are separate.
- **Department details.** Store published details separately from proposed official changes. Name and Core Policies are candidates for the HOD approval allowlist. Headship is a read-only IAM projection once the authoritative contract exists.

Person references use integer IAM IDs. Cross-module foreign keys are excluded. Profile field allowlists and teaching/enrollment scope require authoritative inputs before exposure.

## State transitions

| Record | Current state | Action and actor | Next state |
| --- | --- | --- | --- |
| Announcement | Active | Edit, hide or delete by HOD | Active, hidden or deleted respectively |
| Stock request | Pending HOD approval | Approve or reject by HOD | Approved or rejected |
| Stock request | Approved | Issue by Dept_Admin | Issued |
| Feedback | Submitted | Categorize by Dept_Admin | Reviewed |
| Feedback | Reviewed | Resolve or close by Dept_Admin or HOD | Resolved or closed |
| Official change | Pending | Approve or reject by HOD | Approved or rejected |

The issuance operation aborts if stock has been consumed since approval. It leaves the approved request, quantity and movement log intact. This concurrency behavior is a proposed integrity interpretation for review.

## Permissions and navigation

The first increment uses a Department module grant and `department.announcement.view`. Only the existing basic `student` and `faculty` roles receive that permission in this increment. The navigation item is `department.announcements`, labelled Announcements, icon `Megaphone`, path `/department/announcements`. The module uses the `Buildings` icon, `/department` base path and Department section. It declares no system or scope permissions in this increment.

Later actions require distinct IAM permissions and local data-scope checks. Key HOD and Dept_Admin grants by the actual verified designations and bind them to their authorised department. Keep the external assignment authority with IAM. Use separate permissions for announcement publication and HOD maintenance, stock request/review/issuance, feedback review and final disposition, timetable and lab editing, and official-detail approval.

## Endpoints

| Method and path | Gates | Response and trace |
| --- | --- | --- |
| `GET /api/v1/department/announcements` | Department module grant and `department.announcement.view` | Cursor-paginated active posts visible within the caller's department and target scope. `UC-DEPT-001`, `BR-DEPT-002`, `AFR-DEPT-002` and `AFR-DEPT-003`. |

The `/department/announcements` route uses `RequirePermission` with the same grant. The `/department` index redirects to it. For the external Fusion shell, add the sidebar entry with id `department`, label `Department`, icon `Buildings`, destination `/department`, and section `Department`.

## Contracts

Use IAM's batched `get_users` lookup for active membership, department, programme and batch year. Announcement visibility checks these fields live because the local display cache can retain an old department during an identity change or outage. Unknown and inactive identities produce an empty list. IAM outages return a service-unavailable response. The directory's discipline field is distinct from department. The first increment exports no contracts to other modules.

The planned profile and Headship workflows need IAM contracts for instructor-to-enrollment scope and effective role assignments. Authoritative identity and role data live in IAM. Department owns its business records only.

## Scheduled work

The first increment has no timed transition. Later notification delivery belongs to the action that records the corresponding event. Role tenure and effective handoffs belong to the external IAM contract.

## Decisions and open work

- The current IAM cannot guarantee scoped, time-bounded HOD and Dept_Admin handoffs or derive authoritative Headship. Track `CFR-DEPT-016`, `AFR-DEPT-047`–`053`, `BR-DEPT-021`–`024`, `UC-DEPT-020`/`022`, `BW-DEPT-07`/`08` and `CW-DEPT-04` as open contract dependencies. Initial role bootstrap still needs an explicit rule.
- `BR-DEPT-019` explicitly depends on external privacy policy. Hold detailed profiles and profile writes until the whitelist, course roster and intended lifecycle operations are available.
- For Faculty, limit issued-stock history to their own issued requests. Staff operations remain subject to verified departmental designation scope.
- Announcement publishing, notifications and maintenance are separate future increments. The announcement-read increment alone leaves `AFR-DEPT-046`, mutation and HOD/Dept_Admin scope unimplemented.
- Confirm the concurrency interpretation, official versus general field classification, and timetable scope before implementing those increments.
