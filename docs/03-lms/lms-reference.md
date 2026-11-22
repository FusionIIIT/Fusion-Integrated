# LMS Specification Traceability & Code Reference

Generated automatically by `ops/docs/lms_reference.py`.
Total items verified: 15 CFRs, 47 AFRs, 15 UCs, 19 BRs, 7 Workflows (103 total).

### Coherent Functional Requirements (CFRs)

| ID | Description | Layer | Source File & Line | Status |
|:---|:---|:---|:---|:---|
| `CFR-LMS-001` | Dedicated course workspace access and course home display for authorized users | `selectors` | [selectors/workspace.py:37](../../modules/lms/selectors/workspace.py#L37) | `VERIFIED` |
| `CFR-LMS-002` | Configure assigned course workspace details and edit metadata | `services` | [services/workspace.py:15](../../modules/lms/services/workspace.py#L15) | `VERIFIED` |
| `CFR-LMS-003` | Manage and schedule course materials (files, links, notes) | `services` | [services/materials.py:28](../../modules/lms/services/materials.py#L28) | `VERIFIED` |
| `CFR-LMS-004` | Read-only access to published course materials for authorized users | `selectors` | [selectors/materials.py:19](../../modules/lms/selectors/materials.py#L19) | `VERIFIED` |
| `CFR-LMS-005` | Post and view course-wide announcements | `services` | [services/announcements.py:15](../../modules/lms/services/announcements.py#L15) | `VERIFIED` |
| `CFR-LMS-006` | Create and edit assignments in Draft state | `services` | [services/assignments.py:20](../../modules/lms/services/assignments.py#L20) | `VERIFIED` |
| `CFR-LMS-007` | Publish assignments and control release visibility | `services` | [services/assignments.py:101](../../modules/lms/services/assignments.py#L101) | `VERIFIED` |
| `CFR-LMS-008` | Assignment submission handling (file, text, link) | `services` | [services/submissions.py:41](../../modules/lms/services/submissions.py#L41) | `VERIFIED` |
| `CFR-LMS-009` | Student submission status and history tracking | `selectors` | [selectors/submissions.py:60](../../modules/lms/selectors/submissions.py#L60) | `VERIFIED` |
| `CFR-LMS-010` | Grading student submissions with points and feedback | `services` | [services/grading.py:28](../../modules/lms/services/grading.py#L28) | `VERIFIED` |
| `CFR-LMS-011` | Two-phase grade release workflow (Draft -> Published) | `services` | [services/grading.py:126](../../modules/lms/services/grading.py#L126) | `VERIFIED` |
| `CFR-LMS-012` | Student access to released grade and feedback | `selectors` | [selectors/grading.py:17](../../modules/lms/selectors/grading.py#L17) | `VERIFIED` |
| `CFR-LMS-013` | Audit logging of post-release grade changes | `services` | [services/grading.py:71](../../modules/lms/services/grading.py#L71) | `VERIFIED` |
| `CFR-LMS-014` | Teaching Assistant authority boundaries | `domain` | [domain/rules.py:58](../../modules/lms/domain/rules.py#L58) | `VERIFIED` |
| `CFR-LMS-015` | Observer read-only isolation and student-data privacy | `selectors` | [selectors/scoping.py:69](../../modules/lms/selectors/scoping.py#L69) | `VERIFIED` |

### Atomic Functional Requirements (AFRs)

| ID | Description | Layer | Source File & Line | Status |
|:---|:---|:---|:---|:---|
| `AFR-LMS-001.1` | Open dedicated course workspace when selecting authorized course | `api` | [api/views.py:46](../../modules/lms/api/views.py#L46) | `VERIFIED` |
| `AFR-LMS-001.2` | Display course syllabus, schedule, instructors, and TAs on course home | `selectors` | [selectors/workspace.py:37](../../modules/lms/selectors/workspace.py#L37) | `VERIFIED` |
| `AFR-LMS-001.3` | Restrict course workspace access strictly to authorized/enrolled users | `selectors` | [selectors/scoping.py:13](../../modules/lms/selectors/scoping.py#L13) | `VERIFIED` |
| `AFR-LMS-002.1` | Allow Faculty to configure course workspace settings | `domain` | [domain/rules.py:29](../../modules/lms/domain/rules.py#L29) | `VERIFIED` |
| `AFR-LMS-002.2` | Allow Faculty to publish and edit course details (syllabus, schedule) | `services` | [services/workspace.py:15](../../modules/lms/services/workspace.py#L15) | `VERIFIED` |
| `AFR-LMS-003.1` | Allow Faculty to add materials as files, links, or notes | `domain` | [domain/validators.py:15](../../modules/lms/domain/validators.py#L15) | `VERIFIED` |
| `AFR-LMS-003.2` | Organize materials into modules or weekly sections | `models` | [models/materials.py:21](../../modules/lms/models/materials.py#L21) | `VERIFIED` |
| `AFR-LMS-003.3` | Configure future release date/time for course materials | `domain` | [domain/rules.py:22](../../modules/lms/domain/rules.py#L22) | `VERIFIED` |
| `AFR-LMS-003.4` | Automatically make scheduled material visible when release time is reached | `tasks` | [tasks.py:14](../../modules/lms/tasks.py#L14) | `VERIFIED` |
| `AFR-LMS-004.1` | Students view published course materials in read-only form | `selectors` | [selectors/materials.py:19](../../modules/lms/selectors/materials.py#L19) | `VERIFIED` |
| `AFR-LMS-004.2` | TAs view published course materials in read-only form | `selectors` | [selectors/materials.py:19](../../modules/lms/selectors/materials.py#L19) | `VERIFIED` |
| `AFR-LMS-004.3` | Observers view published course materials in read-only form | `selectors` | [selectors/materials.py:19](../../modules/lms/selectors/materials.py#L19) | `VERIFIED` |
| `AFR-LMS-005.1` | Faculty post course-wide announcements | `services` | [services/announcements.py:15](../../modules/lms/services/announcements.py#L15) | `VERIFIED` |
| `AFR-LMS-005.2` | Permitted TAs post announcements when authorized | `domain` | [domain/rules.py:34](../../modules/lms/domain/rules.py#L34) | `VERIFIED` |
| `AFR-LMS-005.3` | Automatically timestamp posted announcements | `models` | [models/announcements.py:14](../../modules/lms/models/announcements.py#L14) | `VERIFIED` |
| `AFR-LMS-005.4` | Make announcements visible course-wide to enrolled/linked users | `selectors` | [selectors/announcements.py:11](../../modules/lms/selectors/announcements.py#L11) | `VERIFIED` |
| `AFR-LMS-006.1` | Faculty create assignments for assigned courses | `services` | [services/assignments.py:20](../../modules/lms/services/assignments.py#L20) | `VERIFIED` |
| `AFR-LMS-006.2` | Capture required assignment configuration (due date, instructions, points, type) | `domain` | [domain/validators.py:34](../../modules/lms/domain/validators.py#L34) | `VERIFIED` |
| `AFR-LMS-006.3` | Allow Faculty to edit assignment details | `services` | [services/assignments.py:61](../../modules/lms/services/assignments.py#L61) | `VERIFIED` |
| `AFR-LMS-006.4` | Maintain assignment in Draft state before explicit publication | `domain` | [domain/state_machine.py:86](../../modules/lms/domain/state_machine.py#L86) | `VERIFIED` |
| `AFR-LMS-007.1` | Faculty publish draft assignments | `services` | [services/assignments.py:101](../../modules/lms/services/assignments.py#L101) | `VERIFIED` |
| `AFR-LMS-007.2` | Apply release-date visibility control | `selectors` | [selectors/assignments.py:19](../../modules/lms/selectors/assignments.py#L19) | `VERIFIED` |
| `AFR-LMS-007.3` | Release scheduled assignment when release time is reached | `tasks` | [tasks.py:23](../../modules/lms/tasks.py#L23) | `VERIFIED` |
| `AFR-LMS-007.4` | Students view and download assignment instructions once released | `selectors` | [selectors/assignments.py:36](../../modules/lms/selectors/assignments.py#L36) | `VERIFIED` |
| `AFR-LMS-008.1` | Submit work conforming to configured submission type (file/text/link) | `domain` | [domain/validators.py:58](../../modules/lms/domain/validators.py#L58) | `VERIFIED` |
| `AFR-LMS-008.2` | Record and timestamp baseline on-time submission | `domain` | [domain/rules.py:10](../../modules/lms/domain/rules.py#L10) | `VERIFIED` |
| `AFR-LMS-009.1` | Student views own submission history | `selectors` | [selectors/submissions.py:16](../../modules/lms/selectors/submissions.py#L16) | `VERIFIED` |
| `AFR-LMS-009.2` | Student views own submission status (submitted, late, missing) | `domain` | [domain/calculations.py:8](../../modules/lms/domain/calculations.py#L8) | `VERIFIED` |
| `AFR-LMS-010.1` | Faculty grades individual student submissions | `services` | [services/grading.py:28](../../modules/lms/services/grading.py#L28) | `VERIFIED` |
| `AFR-LMS-010.2` | TA grades student submissions for assigned course | `domain` | [domain/rules.py:58](../../modules/lms/domain/rules.py#L58) | `VERIFIED` |
| `AFR-LMS-010.3` | Accurately attribute all grading actions to acting user | `models` | [models/grading.py:22](../../modules/lms/models/grading.py#L22) | `VERIFIED` |
| `AFR-LMS-011.1` | Hold grades in Draft state upon grading | `domain` | [domain/state_machine.py:128](../../modules/lms/domain/state_machine.py#L128) | `VERIFIED` |
| `AFR-LMS-011.2` | Prevent students from viewing unreleased draft grades | `selectors` | [selectors/grading.py:17](../../modules/lms/selectors/grading.py#L17) | `VERIFIED` |
| `AFR-LMS-011.3` | Allow Faculty to release grades and feedback to students | `services` | [services/grading.py:126](../../modules/lms/services/grading.py#L126) | `VERIFIED` |
| `AFR-LMS-012.1` | Student views own released grade and feedback | `selectors` | [selectors/grading.py:17](../../modules/lms/selectors/grading.py#L17) | `VERIFIED` |
| `AFR-LMS-012.2` | Released grade is strictly read-only to Student | `api` | [api/views.py:612](../../modules/lms/api/views.py#L612) | `VERIFIED` |
| `AFR-LMS-013.1` | Record actor identity on post-release grade modification | `models` | [models/grading.py:56](../../modules/lms/models/grading.py#L56) | `VERIFIED` |
| `AFR-LMS-013.2` | Record exact timestamp of post-release grade modification | `models` | [models/grading.py:57](../../modules/lms/models/grading.py#L57) | `VERIFIED` |
| `AFR-LMS-014.1` | TA views course details, materials, and announcements | `selectors` | [selectors/scoping.py:37](../../modules/lms/selectors/scoping.py#L37) | `VERIFIED` |
| `AFR-LMS-014.2` | TA views student submissions for assigned course | `selectors` | [selectors/submissions.py:16](../../modules/lms/selectors/submissions.py#L16) | `VERIFIED` |
| `AFR-LMS-014.3` | TA cannot create, edit, or publish assignments | `domain` | [domain/rules.py:43](../../modules/lms/domain/rules.py#L43) | `VERIFIED` |
| `AFR-LMS-014.4` | TA cannot create or edit course materials | `domain` | [domain/rules.py:48](../../modules/lms/domain/rules.py#L48) | `VERIFIED` |
| `AFR-LMS-014.5` | TA cannot modify course structure or workspace settings | `domain` | [domain/rules.py:53](../../modules/lms/domain/rules.py#L53) | `VERIFIED` |
| `AFR-LMS-015.1` | Observer views course details, materials, announcements | `selectors` | [selectors/workspace.py:37](../../modules/lms/selectors/workspace.py#L37) | `VERIFIED` |
| `AFR-LMS-015.2` | Observer cannot view student submissions | `selectors` | [selectors/submissions.py:16](../../modules/lms/selectors/submissions.py#L16) | `VERIFIED` |
| `AFR-LMS-015.3` | Observer cannot view student grades or student-specific data | `selectors` | [selectors/grading.py:44](../../modules/lms/selectors/grading.py#L44) | `VERIFIED` |
| `AFR-LMS-015.4` | Observer has no write access anywhere in module | `api` | [api/permissions.py:22](../../modules/lms/api/permissions.py#L22) | `VERIFIED` |

### Use Cases (UCs)

| ID | Description | Layer | Source File & Line | Status |
|:---|:---|:---|:---|:---|
| `UC-LMS-001` | Access Course Workspace | `api` | [api/views.py:46](../../modules/lms/api/views.py#L46) | `VERIFIED` |
| `UC-LMS-002` | Manage Course Details | `services` | [services/workspace.py:15](../../modules/lms/services/workspace.py#L15) | `VERIFIED` |
| `UC-LMS-003` | Manage Course Materials | `services` | [services/materials.py:28](../../modules/lms/services/materials.py#L28) | `VERIFIED` |
| `UC-LMS-004` | View Published Course Materials | `selectors` | [selectors/materials.py:19](../../modules/lms/selectors/materials.py#L19) | `VERIFIED` |
| `UC-LMS-005` | Post Course Announcement | `services` | [services/announcements.py:15](../../modules/lms/services/announcements.py#L15) | `VERIFIED` |
| `UC-LMS-006` | View Course Announcements | `selectors` | [selectors/announcements.py:11](../../modules/lms/selectors/announcements.py#L11) | `VERIFIED` |
| `UC-LMS-007` | Create or Edit Assignment | `services` | [services/assignments.py:20](../../modules/lms/services/assignments.py#L20) | `VERIFIED` |
| `UC-LMS-008` | Publish Assignment | `services` | [services/assignments.py:101](../../modules/lms/services/assignments.py#L101) | `VERIFIED` |
| `UC-LMS-009` | View or Download Published Assignment | `selectors` | [selectors/assignments.py:36](../../modules/lms/selectors/assignments.py#L36) | `VERIFIED` |
| `UC-LMS-010` | Submit Assignment | `services` | [services/submissions.py:41](../../modules/lms/services/submissions.py#L41) | `VERIFIED` |
| `UC-LMS-011` | View Submission History and Status | `selectors` | [selectors/submissions.py:60](../../modules/lms/selectors/submissions.py#L60) | `VERIFIED` |
| `UC-LMS-012` | Grade Submission | `services` | [services/grading.py:28](../../modules/lms/services/grading.py#L28) | `VERIFIED` |
| `UC-LMS-013` | Release Grades and Feedback | `services` | [services/grading.py:126](../../modules/lms/services/grading.py#L126) | `VERIFIED` |
| `UC-LMS-014` | View Released Grade and Feedback | `selectors` | [selectors/grading.py:17](../../modules/lms/selectors/grading.py#L17) | `VERIFIED` |
| `UC-LMS-015` | Process Scheduled Content Release | `tasks` | [tasks.py:14](../../modules/lms/tasks.py#L14) | `VERIFIED` |

### Business Rules (BRs)

| ID | Description | Layer | Source File & Line | Status |
|:---|:---|:---|:---|:---|
| `BR-LMS-001` | Course-specific access control | `selectors` | [selectors/scoping.py:37](../../modules/lms/selectors/scoping.py#L37) | `VERIFIED` |
| `BR-LMS-002` | Student registration data governs Student course access | `selectors` | [selectors/scoping.py:81](../../modules/lms/selectors/scoping.py#L81) | `VERIFIED` |
| `BR-LMS-003` | Observer read-only and student-data restriction | `selectors` | [selectors/scoping.py:69](../../modules/lms/selectors/scoping.py#L69) | `VERIFIED` |
| `BR-LMS-004` | TA authoring restriction | `domain` | [domain/rules.py:43](../../modules/lms/domain/rules.py#L43) | `VERIFIED` |
| `BR-LMS-005` | Published material visibility | `selectors` | [selectors/materials.py:19](../../modules/lms/selectors/materials.py#L19) | `VERIFIED` |
| `BR-LMS-006` | Scheduled material release | `tasks` | [tasks.py:14](../../modules/lms/tasks.py#L14) | `VERIFIED` |
| `BR-LMS-007` | Announcement posting authority | `domain` | [domain/rules.py:34](../../modules/lms/domain/rules.py#L34) | `VERIFIED` |
| `BR-LMS-008` | Announcement timestamp and audience | `models` | [models/announcements.py:8](../../modules/lms/models/announcements.py#L8) | `VERIFIED` |
| `BR-LMS-009` | Assignment required configuration | `domain` | [domain/validators.py:34](../../modules/lms/domain/validators.py#L34) | `VERIFIED` |
| `BR-LMS-010` | Assignment draft-before-publication | `domain` | [domain/state_machine.py:86](../../modules/lms/domain/state_machine.py#L86) | `VERIFIED` |
| `BR-LMS-011` | Assignment release-date visibility | `selectors` | [selectors/assignments.py:19](../../modules/lms/selectors/assignments.py#L19) | `VERIFIED` |
| `BR-LMS-012` | Submission-type conformity | `domain` | [domain/validators.py:58](../../modules/lms/domain/validators.py#L58) | `VERIFIED` |
| `BR-LMS-013` | Baseline on-time submission | `domain` | [domain/rules.py:10](../../modules/lms/domain/rules.py#L10) | `VERIFIED` |
| `BR-LMS-014` | Submission ownership and privacy | `selectors` | [selectors/submissions.py:16](../../modules/lms/selectors/submissions.py#L16) | `VERIFIED` |
| `BR-LMS-015` | Grading authority and attribution | `models` | [models/grading.py:22](../../modules/lms/models/grading.py#L22) | `VERIFIED` |
| `BR-LMS-016` | Draft grade visibility | `selectors` | [selectors/grading.py:17](../../modules/lms/selectors/grading.py#L17) | `VERIFIED` |
| `BR-LMS-017` | Grade release authority | `domain` | [domain/rules.py:67](../../modules/lms/domain/rules.py#L67) | `VERIFIED` |
| `BR-LMS-018` | Released grade read-only to Student | `api` | [api/views.py:612](../../modules/lms/api/views.py#L612) | `VERIFIED` |
| `BR-LMS-019` | Post-release grade-change audit | `services` | [services/grading.py:71](../../modules/lms/services/grading.py#L71) | `VERIFIED` |

### Workflows (BWs & CWs)

| ID | Description | Layer | Source File & Line | Status |
|:---|:---|:---|:---|:---|
| `BW-LMS-01` | Scheduled Course Material Release | `domain` | [domain/state_machine.py:56](../../modules/lms/domain/state_machine.py#L56) | `VERIFIED` |
| `BW-LMS-02` | Assignment Immediate Release and On-Time Submission | `domain` | [domain/state_machine.py:86](../../modules/lms/domain/state_machine.py#L86) | `VERIFIED` |
| `BW-LMS-03` | Assignment Scheduled Release and On-Time Submission | `tasks` | [tasks.py:14](../../modules/lms/tasks.py#L14) | `VERIFIED` |
| `BW-LMS-04` | Faculty Grading and Grade Release | `domain` | [domain/state_machine.py:128](../../modules/lms/domain/state_machine.py#L128) | `VERIFIED` |
| `BW-LMS-05` | TA Grading and Faculty Grade Release | `services` | [services/grading.py:28](../../modules/lms/services/grading.py#L28) | `VERIFIED` |
| `CW-LMS-01` | Assignment Publication and Submission | `domain` | [domain/state_machine.py:158](../../modules/lms/domain/state_machine.py#L158) | `VERIFIED` |
| `CW-LMS-02` | Grading and Grade Release | `domain` | [domain/state_machine.py:167](../../modules/lms/domain/state_machine.py#L167) | `VERIFIED` |
