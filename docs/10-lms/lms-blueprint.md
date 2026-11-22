# LMS (Course Management) blueprint

**Version:** A9-LMS-BP-0.1  
**Prepared:** 22 November 2026 (IST)  
**Status:** DRAFT — blocked; application implementation not authorized  
**Branch:** `module/lms`  
**Proposed location:** `docs/10-lms/lms-blueprint.md`; pair endorsement received, instructor identifier confirmation pending  
**Platform base:** `5595be6628b4cdc6f8b47cf74bac267a2470f780`  
**IAM source inspected:** `d143e4e61b11a2a5e21c03355f8b784d83103b5d`

This document is a source-derived design draft. It does not claim that the module, registry, routes, tasks, storage extension or IAM endpoints already exist. The named enforcement points below are planned module functions, not promises of a currently available external API. Application code remains on hold under the received ruling and builder prompt Step 3.6.

Inputs are the six original LMS v1.0 specification artifacts and the formal D-01–D-06 ruling received on 22 November 2026. The unmodified ruling is preserved in the external review record, SHA-256 `9199d3a2259d6bcb6fb29d421fc5d9c679823e789d86c5731b4fe808e38bfacb`. Policy detail is in [policy-decisions.md](policy-decisions.md). Original obligations and later policy clarifications are distinguished throughout. The four preliminary Student 2 test-design files are not design authority for this blueprint.

## 3.1 — Traceability table

All 103 live IDs are listed once: 15 CFRs, 47 AFRs, 19 BRs, 15 UCs, five BWs and two CWs. No retired IDs were identified. The supplied main CFR/AFR mapping columns are blank, so enforcement is derived from the source clauses rather than assumed matrix links. A parent CFR's children do not require redundant tests when the same obligation is already covered.

| ID | What it requires | Layer | Planned enforcement point | Notes |
|---|---|---|---|---|
| CFR-LMS-001 | The system shall provide a dedicated course workspace for each course and allow an authorized course user to open that workspace and view the course home information for the specific course to which the user is enrolled in, assigned to, or otherwise linked. | selectors + services | selectors/scoping.py; services/workspaces.py::open_workspace | Authoritative course associations are blocked by BPR-001. |
| CFR-LMS-002 | The system shall allow Faculty to own/configure the workspace for assigned courses and to publish and edit the course details presented in that workspace. | services + models | services/workspaces.py::update_details; models/workspaces.py | Faculty must be assigned to the selected offering. |
| CFR-LMS-003 | The system shall allow Faculty to upload course materials as files, links, or notes, organize them into modules or weekly sections, and optionally schedule a future release date. | domain + services + tasks | services/materials.py; domain/releases.py; tasks.py::release_due_materials | Real file support requires the shared-file decision in BPR-005. |
| CFR-LMS-004 | The system shall provide Students, TAs, and Observers with read-only access to published course materials for courses they are authorized to access. | selectors + API | selectors/materials.py::visible_materials; read-only serializers | Only released material in the actor's course scope. |
| CFR-LMS-005 | The system shall allow Faculty, and TAs where permitted, to post timestamped course-wide announcements and shall make posted announcements visible to all users enrolled in or linked to the course. | domain + services + selectors | services/announcements.py::post_announcement; domain/capabilities.py | D-02 TA posting flag; D-03 visibility only. |
| CFR-LMS-006 | The system shall allow Faculty to create and edit an assignment for an assigned course, capturing due date, instructions, submission type, and points possible, with the assignment remaining in Draft state before publication. | domain + models + services | services/assignments.py::save_draft; domain/assignment_rules.py | Required configuration and Draft state. |
| CFR-LMS-007 | The system shall allow Faculty to publish an assignment and shall control Student visibility according to the configured release date; Students shall be able to view and download assignments once released. | domain + services + selectors + tasks | services/assignments.py::publish; selectors/assignments.py; tasks.py::release_due_assignments | Published/Scheduled and Available are distinct. |
| CFR-LMS-008 | The system shall allow a Student to submit assignment work using the submission type configured by Faculty and shall support the baseline on-time submission case before the due date. | domain + models + services | services/submissions.py::create_submission; domain/submission_rules.py | D-01 exact UTC boundary; D-05 one successful submission. |
| CFR-LMS-009 | The system shall allow a Student to view only the Student’s own assignment submission history and submission status, including submitted, late, or missing where applicable. | selectors + API | selectors/submissions.py::own_history; status DTO | Missing is derived; the adopted baseline does not create late submissions. |
| CFR-LMS-010 | The system shall allow Faculty and TAs to grade individual submissions by entering points and feedback, and shall attribute each grading action to the person who performed it. | domain + services + models | services/grading.py::save_grade; models/grading.py::GradeAuditLog | Every grading action has actor/time attribution; D-06 governs released edits. |
| CFR-LMS-011 | The system shall keep grades and feedback in Draft state until Faculty releases them, shall prevent Students from seeing draft grades, and shall make released grades/feedback available to the applicable Student. | domain + services + selectors | services/grading.py::release_grade; selectors/grades.py | Only Faculty releases; students see no Draft score or feedback. |
| CFR-LMS-012 | The system shall allow a Student to view the Student’s own released grade and feedback in read-only form. | selectors + API | selectors/grades.py::own_released_grades; read-only serializers | Student reads only their own Released grade. |
| CFR-LMS-013 | Whenever a released grade is changed, the system shall log the change and record who made the change and when it was made. | services + models | services/grading.py::change_released_grade; GradeAuditLog | Original actor/time obligation plus separately attributed D-06 extension. |
| CFR-LMS-014 | The system shall provide TAs with course viewing, submission-viewing and grading capabilities for assigned courses, while preventing TAs from creating or editing assignments, materials, or course structure; announcement posting is allowed only where permitted. | registry + domain + selectors | registry.py; domain/capabilities.py; selectors/scoping.py | TA designation unresolved; never grant authoring as a workaround. |
| CFR-LMS-015 | The system shall provide an Observer with read-only access to course details, published materials, and announcements for the linked course while preventing access to individual submissions, grades, and other Student-specific data and preventing all write actions. | registry + selectors + API | registry.py; selectors/scoping.py; audience-specific serializers | D-04 course linkage; no student-specific reads or any writes. |
| AFR-LMS-001.1 | The system shall open a dedicated course workspace when a user selects a course for which the user has authorized course access. | selectors + services | selectors/scoping.py; services/workspaces.py::open_workspace | Authoritative course associations are blocked by BPR-001. |
| AFR-LMS-001.2 | The system shall display the course syllabus, schedule, instructor(s), and TA(s) on the course home page. | selectors + services | selectors/scoping.py; services/workspaces.py::open_workspace | Authoritative course associations are blocked by BPR-001. |
| AFR-LMS-001.3 | The system shall restrict a course workspace to users enrolled in, assigned to, or linked to that specific course. | selectors + services | selectors/scoping.py; services/workspaces.py::open_workspace | Authoritative course associations are blocked by BPR-001. |
| AFR-LMS-002.1 | The system shall allow Faculty to configure the course workspace for courses assigned to that Faculty member. | services + models | services/workspaces.py::update_details; models/workspaces.py | Faculty must be assigned to the selected offering. |
| AFR-LMS-002.2 | The system shall allow Faculty to publish and edit course details for an assigned course workspace. | services + models | services/workspaces.py::update_details; models/workspaces.py | Faculty must be assigned to the selected offering. |
| AFR-LMS-003.1 | The system shall allow Faculty to add course materials as files, links, or notes. | domain + services + tasks | services/materials.py; domain/releases.py; tasks.py::release_due_materials | Real file support requires the shared-file decision in BPR-005. |
| AFR-LMS-003.2 | The system shall allow Faculty to organize course materials into modules or weekly sections. | domain + services + tasks | services/materials.py; domain/releases.py; tasks.py::release_due_materials | Real file support requires the shared-file decision in BPR-005. |
| AFR-LMS-003.3 | The system shall allow Faculty to configure a future release date for course material. | domain + services + tasks | services/materials.py; domain/releases.py; tasks.py::release_due_materials | Real file support requires the shared-file decision in BPR-005. |
| AFR-LMS-003.4 | When a scheduled material release time is reached, the system shall make that material published/available to authorized course users. | domain + services + tasks | services/materials.py; domain/releases.py; tasks.py::release_due_materials | Real file support requires the shared-file decision in BPR-005. |
| AFR-LMS-004.1 | The system shall allow a Student to view published course materials for the Student’s registered course in read-only form. | selectors + API | selectors/materials.py::visible_materials; read-only serializers | Only released material in the actor's course scope. |
| AFR-LMS-004.2 | The system shall allow a TA to view published course materials for the assigned course in read-only form. | selectors + API | selectors/materials.py::visible_materials; read-only serializers | Only released material in the actor's course scope. |
| AFR-LMS-004.3 | The system shall allow an Observer to view published course materials for the linked course in read-only form. | selectors + API | selectors/materials.py::visible_materials; read-only serializers | Only released material in the actor's course scope. |
| AFR-LMS-005.1 | The system shall allow Faculty to post a course-wide announcement for an assigned course. | domain + services + selectors | services/announcements.py::post_announcement; domain/capabilities.py | D-02 TA posting flag; D-03 visibility only. |
| AFR-LMS-005.2 | The system shall allow a TA to post a course-wide announcement only where the TA is permitted to do so for that course. | domain + services + selectors | services/announcements.py::post_announcement; domain/capabilities.py | D-02 TA posting flag; D-03 visibility only. |
| AFR-LMS-005.3 | The system shall timestamp each posted course announcement. | domain + services + selectors | services/announcements.py::post_announcement; domain/capabilities.py | D-02 TA posting flag; D-03 visibility only. |
| AFR-LMS-005.4 | The system shall make a posted course announcement visible to all users enrolled in or linked to that course. | domain + services + selectors | services/announcements.py::post_announcement; domain/capabilities.py | D-02 TA posting flag; D-03 visibility only. |
| AFR-LMS-006.1 | The system shall allow Faculty to create an assignment for an assigned course. | domain + models + services | services/assignments.py::save_draft; domain/assignment_rules.py | Required configuration and Draft state. |
| AFR-LMS-006.2 | The system shall capture an assignment due date, instructions, submission type, and points possible. | domain + models + services | services/assignments.py::save_draft; domain/assignment_rules.py | Required configuration and Draft state. |
| AFR-LMS-006.3 | The system shall allow Faculty to edit an assignment. | domain + models + services | services/assignments.py::save_draft; domain/assignment_rules.py | Required configuration and Draft state. |
| AFR-LMS-006.4 | The system shall keep an assignment in Draft state until Faculty publishes it. | domain + models + services | services/assignments.py::save_draft; domain/assignment_rules.py | Required configuration and Draft state. |
| AFR-LMS-007.1 | The system shall allow Faculty to publish an assignment. | domain + services + selectors + tasks | services/assignments.py::publish; selectors/assignments.py; tasks.py::release_due_assignments | Published/Scheduled and Available are distinct. |
| AFR-LMS-007.2 | The system shall withhold a published assignment from Students until its configured release date/time. | domain + services + selectors + tasks | services/assignments.py::publish; selectors/assignments.py; tasks.py::release_due_assignments | Published/Scheduled and Available are distinct. |
| AFR-LMS-007.3 | When the configured assignment release time is reached, the system shall make the assignment available to authorized Students. | domain + services + selectors + tasks | services/assignments.py::publish; selectors/assignments.py; tasks.py::release_due_assignments | Published/Scheduled and Available are distinct. |
| AFR-LMS-007.4 | The system shall allow a Student to view and download an assignment after it has been released for the Student’s registered course. | domain + services + selectors + tasks | services/assignments.py::publish; selectors/assignments.py; tasks.py::release_due_assignments | Published/Scheduled and Available are distinct. |
| AFR-LMS-008.1 | The system shall allow a Student to submit assignment work as a file, text, or link according to the assignment’s configured submission type. | domain + models + services | services/submissions.py::create_submission; domain/submission_rules.py | D-01 exact UTC boundary; D-05 one successful submission. |
| AFR-LMS-008.2 | The system shall accept and record a Student submission made before the assignment due date. | domain + models + services | services/submissions.py::create_submission; domain/submission_rules.py | D-01 exact UTC boundary; D-05 one successful submission. |
| AFR-LMS-009.1 | The system shall allow a Student to view the Student’s own submission history for an assignment. | selectors + API | selectors/submissions.py::own_history; status DTO | Missing is derived; the adopted baseline does not create late submissions. |
| AFR-LMS-009.2 | The system shall show the Student’s own submission status as submitted, late, or missing where applicable. | selectors + API | selectors/submissions.py::own_history; status DTO | Missing is derived; the adopted baseline does not create late submissions. |
| AFR-LMS-010.1 | The system shall allow Faculty to grade an individual Student submission by entering points and feedback. | domain + services + models | services/grading.py::save_grade; models/grading.py::GradeAuditLog | Every grading action has actor/time attribution; D-06 governs released edits. |
| AFR-LMS-010.2 | The system shall allow a TA to grade an individual Student submission for the assigned course by entering points and feedback. | domain + services + models | services/grading.py::save_grade; models/grading.py::GradeAuditLog | Every grading action has actor/time attribution; D-06 governs released edits. |
| AFR-LMS-010.3 | The system shall record the identity of the Faculty member or TA who performs a grading action. | domain + services + models | services/grading.py::save_grade; models/grading.py::GradeAuditLog | Every grading action has actor/time attribution; D-06 governs released edits. |
| AFR-LMS-011.1 | The system shall keep a grade and feedback in Draft state until release. | domain + services + selectors | services/grading.py::release_grade; selectors/grades.py | Only Faculty releases; students see no Draft score or feedback. |
| AFR-LMS-011.2 | The system shall prevent a Student from viewing a grade or feedback before it is released. | domain + services + selectors | services/grading.py::release_grade; selectors/grades.py | Only Faculty releases; students see no Draft score or feedback. |
| AFR-LMS-011.3 | The system shall allow Faculty to release draft grades and feedback to Students. | domain + services + selectors | services/grading.py::release_grade; selectors/grades.py | Only Faculty releases; students see no Draft score or feedback. |
| AFR-LMS-012.1 | The system shall allow a Student to view the Student’s own grade and feedback after release. | selectors + API | selectors/grades.py::own_released_grades; read-only serializers | Student reads only their own Released grade. |
| AFR-LMS-012.2 | The system shall present released grade and feedback to the Student in read-only form. | selectors + API | selectors/grades.py::own_released_grades; read-only serializers | Student reads only their own Released grade. |
| AFR-LMS-013.1 | When a released grade is changed, the system shall record who made the change. | services + models | services/grading.py::change_released_grade; GradeAuditLog | Original actor/time obligation plus separately attributed D-06 extension. |
| AFR-LMS-013.2 | When a released grade is changed, the system shall record when the change was made. | services + models | services/grading.py::change_released_grade; GradeAuditLog | Original actor/time obligation plus separately attributed D-06 extension. |
| AFR-LMS-014.1 | The system shall allow a TA to view course details, published materials, and announcements for the assigned course. | registry + domain + selectors | registry.py; domain/capabilities.py; selectors/scoping.py | TA designation unresolved; never grant authoring as a workaround. |
| AFR-LMS-014.2 | The system shall allow a TA to view Student submissions for the assigned course. | registry + domain + selectors | registry.py; domain/capabilities.py; selectors/scoping.py | TA designation unresolved; never grant authoring as a workaround. |
| AFR-LMS-014.3 | The system shall prevent a TA from creating or editing assignments. | registry + domain + selectors | registry.py; domain/capabilities.py; selectors/scoping.py | TA designation unresolved; never grant authoring as a workaround. |
| AFR-LMS-014.4 | The system shall prevent a TA from creating or editing course materials. | registry + domain + selectors | registry.py; domain/capabilities.py; selectors/scoping.py | TA designation unresolved; never grant authoring as a workaround. |
| AFR-LMS-014.5 | The system shall prevent a TA from modifying course structure. | registry + domain + selectors | registry.py; domain/capabilities.py; selectors/scoping.py | TA designation unresolved; never grant authoring as a workaround. |
| AFR-LMS-015.1 | The system shall allow an Observer to view course details, published materials, and announcements for the linked course in read-only form. | registry + selectors + API | registry.py; selectors/scoping.py; audience-specific serializers | D-04 course linkage; no student-specific reads or any writes. |
| AFR-LMS-015.2 | The system shall prevent an Observer from viewing individual Student submissions. | registry + selectors + API | registry.py; selectors/scoping.py; audience-specific serializers | D-04 course linkage; no student-specific reads or any writes. |
| AFR-LMS-015.3 | The system shall prevent an Observer from viewing grades or any other Student-specific data. | registry + selectors + API | registry.py; selectors/scoping.py; audience-specific serializers | D-04 course linkage; no student-specific reads or any writes. |
| AFR-LMS-015.4 | The system shall prevent an Observer from performing write actions anywhere in the LMS Course Management module. | registry + selectors + API | registry.py; selectors/scoping.py; audience-specific serializers | D-04 course linkage; no student-specific reads or any writes. |
| BR-LMS-001 | A user may access a course workspace only for a course in which the user is enrolled, assigned, or otherwise linked. | selectors + contracts | selectors/scoping.py::accessible_workspaces | BPR-001; out-of-scope resources are 404. |
| BR-LMS-002 | Student course access shall be based on the existing Fusion course-registration data; this module shall not redefine registration/add-drop/waitlist rules. | contracts + selectors | approved IAM course-association contract; selectors/scoping.py | No local enrollment authority or direct ERP connection. |
| BR-LMS-003 | An Observer may read course details, published materials, and announcements for the linked course, but may not view individual submissions, grades, or other Student-specific data and may not perform any write action. | domain + selectors + API | domain/capabilities.py; audience-specific serializers | D-04; exclude submissions, grades and rosters. |
| BR-LMS-004 | A TA may view permitted course content, view submissions, grade, and post announcements where permitted, but may not create/edit assignments, materials, or course structure. | registry + domain | registry.py; domain/capabilities.py | D-02; TA read/grade only, with conditional announcements. |
| BR-LMS-005 | Students, TAs, and Observers may view course materials only after those materials are published/released for the course. | selectors | selectors/materials.py::visible_materials | Students/TAs/Observers see Published only. |
| BR-LMS-006 | A course material configured with a future release date shall remain unavailable until that release date/time is reached. | domain + tasks | domain/releases.py; tasks.py::release_due_materials | Never release before the configured aware UTC instant. |
| BR-LMS-007 | Faculty may post course announcements; a TA may post only where permitted by Faculty for that course. | domain + services | domain/capabilities.py; services/announcements.py | D-02; course policy version defaults posting flag to false. |
| BR-LMS-008 | Each posted announcement shall be timestamped and visible to all users enrolled in or linked to the course. | services + selectors | services/announcements.py; created_at; course-scoped list | D-03 does not require outbound notifications. |
| BR-LMS-009 | An assignment must define due date, instructions, submission type, and points possible before publication. | API + domain + services | assignment serializers; domain/assignment_rules.py | Required request fields versus semantic publication validation. |
| BR-LMS-010 | An assignment shall remain in Draft state before Faculty publishes it. | domain + models | domain/state_machine.py; Assignment.status | Creating/editing a draft does not publish it. |
| BR-LMS-011 | A published assignment shall become visible to Students only when its configured release date/time condition is satisfied. | domain + selectors + tasks | domain/releases.py; selectors/assignments.py; release task | Future release remains unavailable until the scheduled transition. |
| BR-LMS-012 | A Student submission must use the submission type configured for the assignment: file, text, or link. | domain + services | domain/submission_rules.py::validate_payload_kind | FILE/TEXT/LINK must match the configured submission kind. |
| BR-LMS-013 | The current baseline explicitly supports Student submission before the due date; late-submission behavior is unresolved and shall not be invented. | domain + services | domain/submission_rules.py::validate_deadline | D-01 adopts <= due_at; > due_at is 422 SUBMISSION_DUE_DATE_EXCEEDED. |
| BR-LMS-014 | A Student may view only the Student’s own submission history and status. | selectors | selectors/submissions.py::own_history | Owner is principal.user_id, never a client-supplied owner. |
| BR-LMS-015 | Faculty and TAs may grade individual submissions for the applicable course, and each grading action shall be attributed to the person who performed it. | domain + services + models | services/grading.py::save_grade; GradeAuditLog | Faculty/TA course role required; preserve each grading actor. |
| BR-LMS-016 | Grades and feedback shall remain Draft and invisible to Students until released. | selectors + domain | selectors/grades.py::own_released_grades; grade transitions | No draft scores or feedback in Student responses. |
| BR-LMS-017 | Under the current baseline, Faculty releases grades and feedback to Students; TA grading does not by itself release grades. | registry + domain + services | services/grading.py::release_grade | TA grading never releases a grade; D-02. |
| BR-LMS-018 | After release, a Student may view the Student’s own grade and feedback in read-only form. | selectors + API | read-only Student grade DTO; no Student grade write permission | Only the corresponding Student's released data. |
| BR-LMS-019 | Whenever a released grade is changed, the system shall log the change, recording who made it and when. | services + models | atomic released-grade update and GradeAuditLog insert | D-06 adds Faculty-only authority, retained Released state and old/new values. |
| UC-LMS-001 | Access Course Workspace: Open the dedicated workspace for a course the user is authorized to access and view course-home information. | services + selectors | services/workspaces.py::open_workspace | Association outage fails closed; UC access-denial paths retained. |
| UC-LMS-002 | Manage Course Details: Configure the assigned course workspace and publish/edit course details. | services | services/workspaces.py::update_details | Assigned Faculty only; updates must not alter source memberships. |
| UC-LMS-003 | Manage Course Materials: Add and organize course materials and optionally schedule their release. | domain + services | services/materials.py | File/link/note; organization; immediate/future release; no TA/Student/Observer writes. |
| UC-LMS-004 | View Published Course Materials: View published course materials for an authorized course. | selectors + API | selectors/materials.py::visible_materials | Read-only Published content, including direct-resource requests. |
| UC-LMS-005 | Post Course Announcement: Post a course-wide announcement. | services + domain | services/announcements.py::post_announcement | Faculty or course TA when D-02 flag is true. |
| UC-LMS-006 | View Course Announcements: Read course-wide announcements for an authorized course. | selectors + API | selectors/announcements.py::course_announcements | Course association, timestamp and contents. |
| UC-LMS-007 | Create or Edit Assignment: Create or edit an assignment and maintain it in Draft state until publication. | services + domain | services/assignments.py::save_draft | Create/edit Draft with required configuration. |
| UC-LMS-008 | Publish Assignment: Publish a Draft assignment and establish its release timing. | services + domain | services/assignments.py::publish | Immediate and scheduled outcomes; refuse invalid draft. |
| UC-LMS-009 | View or Download Published Assignment: View/download an assignment after it is released. | selectors + API | selectors/assignments.py; assignment instructions download | Registered Student; withhold unreleased assignments. |
| UC-LMS-010 | Submit Assignment: Submit assignment work using the configured submission type. | services + domain + models | services/submissions.py::create_submission | D-01/D-05; type match, UTC timestamp, one successful attempt. |
| UC-LMS-011 | View Submission History and Status: View own assignment submission history and status. | selectors + API | selectors/submissions.py::own_history | Own data only; derive missing/submitted without inventing late acceptance. |
| UC-LMS-012 | Grade Submission: Grade an individual Student submission by recording points and feedback. | services + domain + models | services/grading.py::save_grade/change_released_grade | D-06; immutable action attribution; unauthorized course/grader refused. |
| UC-LMS-013 | Release Grades and Feedback: Release draft grades/feedback to Students. | services + domain | services/grading.py::release_grade | Faculty-only Draft -> Released. |
| UC-LMS-014 | View Released Grade and Feedback: View own released grade and feedback in read-only form. | selectors + API | selectors/grades.py::own_released_grades | Hide Draft and other Students' data. |
| UC-LMS-015 | Process Scheduled Content Release: Make scheduled course material or an assignment available when its configured release time is reached. | tasks + domain + services | release_due_materials/release_due_assignments | System actor, due-time guard, no release of withdrawn content; record processing failures. |
| BW-LMS-01 | Scheduled Course Material Release | domain + services + tasks | services/materials.py; release_due_materials | Draft -> Scheduled -> Published; Faculty then System. |
| BW-LMS-02 | Assignment Immediate Release and On-Time Submission | domain + services + tasks | services/assignments.py; services/submissions.py | New -> Draft -> Available -> recorded submission. |
| BW-LMS-03 | Assignment Scheduled Release and On-Time Submission | domain + services + tasks | services/assignments.py; release_due_assignments; services/submissions.py | New -> Draft -> Scheduled -> Available -> recorded submission. |
| BW-LMS-04 | Faculty Grading and Grade Release | domain + services + tasks | services/grading.py | Recorded submission -> Draft grade -> Faculty release. |
| BW-LMS-05 | TA Grading and Faculty Grade Release | domain + services + tasks | services/grading.py | TA draft grading -> Faculty release. |
| CW-LMS-01 | Assignment Publication and Submission | domain + services + tasks | assignment transition table + submission service | Both BW-LMS-02 immediate and BW-LMS-03 scheduled paths; no unsupported late/resubmission path. |
| CW-LMS-02 | Grading and Grade Release | domain + services + tasks | grade transition table + grading service | Both Faculty-grading and TA-grading branches; Faculty-only release. |

## 3.2 — Domain model and constraints

### Ownership and types

All LMS business tables live in `fusion_integrated`. Each aggregate uses `TimeStampedModel`; person-owned submissions use `UserScopedModel`. Every actor/owner/grader reference is a plain integer IAM `user_id`, never a foreign key to a user or another module. Foreign keys below stay within `modules.lms`.

The authoritative offering identifier's final wire type, stability and term/section semantics depend on BPR-001. `external_offering_key` below is a logical field, not an invented supported IAM identifier. Finalize its database representation only after receiving the real contract. Source-owned instructor/TA assignments and membership are not copied into a locally editable LMS authority.

| Planned entity | Fields and purpose | Database constraints / invariants |
|---|---|---|
| `CourseWorkspace` | Authoritative external offering key; LMS-owned syllabus and schedule text; details publication timestamp; configuring actor ID. Instructor/TA display comes from the approved source and existing user-directory enrichment. | Unique authoritative offering key (`lms_workspace_offering_uniq`); no editable enrollment/assignment fields. Data type blocked by the upstream contract. |
| `CoursePolicyVersion` | Workspace, monotonically increasing version, effective-from UTC timestamp, `can_ta_post_announcements` (default false), policy decision version and author ID. | Unique `(workspace, version)` and `(workspace, effective_from)`; append new versions instead of editing prior policy. Under a workspace row lock, select the latest version effective at the action timestamp. No policy means the documented safe default, not a 500. |
| `MaterialSection` | Workspace, grouping kind (module or week), label and display order. | Workspace-local relationship; nonnegative order (`lms_section_order_nonnegative`); scoped section IDs validated on writes. |
| `Material` | Workspace, optional section, content kind FILE/LINK/NOTE, note body/link/file reference, order, state DRAFT/SCHEDULED/PUBLISHED, release time, author ID and publication timestamp. | State/kind check constraints; exactly the payload appropriate to the kind; SCHEDULED requires release time. Section and material workspace must agree, enforced transactionally. Named scope/state/release-time indexes match listing and due-content scans. |
| `Announcement` | Workspace, content, author ID and server-created timestamp. | Nonempty content validated before insert; author immutable. D-03 requires course-scoped pull visibility only. |
| `Assignment` | Workspace, instructions, due timestamp, submission kind FILE/TEXT/LINK, points possible, state DRAFT/SCHEDULED/AVAILABLE, optional release timestamp, author and publishing actor IDs. | Kind/state checks; points possible nonnegative (`lms_assignment_points_nonnegative`); required configuration before publication; SCHEDULED requires a release timestamp. No unapproved bonus-score, date-order or withdrawal rule is silently added. |
| `Submission` | Workspace-local assignment FK, owner `user_id`, content kind and exactly one file/text/link payload, authoritative `submitted_at`, policy decision version used. A persisted row represents a successfully recorded submission. | Unique `(assignment, user_id)` (`lms_submission_assignment_user_uniq`) implements D-05 under concurrent requests. Payload-kind and local relationship checks; owner/time are server-owned. Rejected validation creates no row and consumes no attempt. |
| `Grade` | One-to-one local submission FK, points, feedback, state DRAFT/RELEASED, last grader ID/time, releasing Faculty ID/time. | One grade per submission; nonnegative points (`lms_grade_points_nonnegative`); RELEASED requires release actor/time. Student has no write path. No upper-score cap is invented beyond approved policy/source constraints. |
| `GradeAuditLog` | Local submission FK, actor ID, operation, previous/new score, previous/new feedback, previous/new state, server UTC `changed_at`. | Append-only through the grading service; no update/delete API. Parent rows protected from deletion. Every grading action is attributed; D-06 released edits require all specified before/after fields in the same transaction as the grade update. |
| `StoredFile` | Workspace and owner ID, opaque storage key, sanitized original name, content-detected media type, size, digest and creation time. Used only by material/submission file variants. | No public storage URL or filesystem path in API output. Opaque unique key; storage outside repository/web root; download authorization follows the parent resource. Core upload writer/type/size validation is currently absent: BPR-005. |

Text/link/file exclusivity and legal-state checks belong in named database `CheckConstraint`s wherever expressible. The submission uniqueness constraint is mandatory even when a service also checks for an existing row. Cross-row rules (same workspace, actor association, grading cap if later approved) belong in the transactional service/domain boundary, not a misleading cross-table check constraint.

### Transaction boundaries

- `services/submissions.py::create_submission` narrows the course/assignment scope, verifies active-role authority, locks the assignment, obtains one authoritative aware UTC server timestamp, validates availability/type/deadline, stages any validated file, and inserts one submission atomically. A concurrent unique collision becomes `409 SUBMISSION_ALREADY_EXISTS`. A late request becomes `422 SUBMISSION_DUE_DATE_EXCEEDED`. Validation/storage failure leaves no submission and cleans up newly staged bytes.
- `services/grading.py::save_grade` locks the submission and grade in a consistent order. Faculty/assigned TA may create or update Draft grades. The service records each actor/time event. It does not release a grade as a side effect of grading.
- `release_grade` is the Faculty-only DRAFT → RELEASED choke point. `change_released_grade` is Faculty-only, retains RELEASED and writes the required immutable audit row atomically. Rollback prevents a grade change without its audit record.
- Material and assignment state changes go through their service transition function with row locks. Scheduled processing calls that same function; it never bypasses guards with a bulk status update.
- Course settings changes append an effective-dated policy version under a workspace lock. They never edit old policy rows.

There is no money/quota ledger: LMS points are an assessment score, not a spendable balance. D-05 is a uniqueness rule over successfully recorded submissions, not a mutable attempt counter.

## 3.3 — Declarative state machines

State/event/actor/target/guards will be immutable transition data in `domain/state_machine.py`. The domain imports no Django, DRF, Celery, settings or `core.api` exceptions. Services translate plain domain exceptions to the shared API error classes. No default transition or permissive fallback exists.

### Material

| From | Event | Actor | To | Guards / authority |
|---|---|---|---|---|
| Absent | Save material | Faculty | DRAFT | Assigned offering; valid FILE/LINK/NOTE payload; section in same workspace |
| DRAFT | Publish now | Faculty | PUBLISHED | Valid payload; immediate release; BR-LMS-005 |
| DRAFT | Schedule | Faculty | SCHEDULED | Valid payload; future aware release time; BW-LMS-01 row 1 |
| SCHEDULED | Release due | System | PUBLISHED | Still scheduled, eligible and `release_at <= now`; BW-LMS-01 row 2 |
| SCHEDULED | Withdraw/unpublish before release | Faculty | DRAFT | UC-LMS-015 alternative; cancel eligibility, never expose content |

Editing content/organization within its current state is an explicit service operation with the same authoring scope; it is not a new basis workflow. Re-scheduling from a scheduled state must be represented explicitly with a future-time guard. Any other proposed lifecycle requires a source or separately approved ruling.

### Assignment and submission

| From | Event | Actor | To | Guards / authority |
|---|---|---|---|---|
| Absent | Save assignment | Faculty | DRAFT | Required draft configuration; assigned course; UC-LMS-007 |
| DRAFT | Edit draft | Faculty | DRAFT | Valid configuration; no publication side effect |
| DRAFT | Publish immediately | Faculty | AVAILABLE | Publication valid and release condition satisfied; BW-LMS-02/CW-LMS-01 |
| DRAFT | Publish for future release | Faculty | SCHEDULED | Publication valid and future release time; BW-LMS-03/CW-LMS-01 |
| SCHEDULED | Release due | System | AVAILABLE | Still eligible; `release_at <= now`; UC-LMS-015 |
| SCHEDULED | Withdraw/unpublish before release | Faculty | DRAFT | UC-LMS-015 alternative; no premature exposure |
| AVAILABLE + no submission for actor | Submit | Student | AVAILABLE + one recorded submission | Authoritative registration, correct kind, `now <= due_at`, no prior recorded submission; D-01/D-05 |

The source does not define a global CLOSED assignment state. Due dates gate submissions without inventing that state. Assignment availability is not consumed by one student's submission. D-05 prohibits later replacement of the successful submission; malformed/type-invalid/late requests consume nothing. D-01 is the explicit clarification admitting exact equality at the deadline; D-05's phrase “before the due date” is applied using that exact D-01 boundary.

### Grade

| From | Event | Actor | To | Guards / authority |
|---|---|---|---|---|
| No grade | Save evaluation | Faculty / TA | DRAFT | Assigned grading role, existing scoped submission, valid points/feedback, actor attribution |
| DRAFT | Edit evaluation | Faculty / TA | DRAFT | Same scope; append grading attribution event |
| DRAFT | Release grade | Faculty | RELEASED | Release permission and course role; releasing actor/time recorded |
| RELEASED | Correct score/feedback | Faculty | RELEASED | D-06; same-transaction before/after audit; uninterrupted Student visibility |

There is no TA release edge and no TA released-edit edge. Students and Observers have no grade-write edges. Missing edges are refused; the service distinguishes permission failure from a lifecycle conflict.

BW-LMS-04 and BW-LMS-05 differ in the actor of the first grading edge. CW-LMS-02 covers those alternatives without adding another synthetic workflow. CW-LMS-01 covers both assignment publication paths. D-06 adds an explicitly attributed policy clarification; it is not retroactively described as a new workflow ID in the unchanged v1.0 registry.

## 3.4 — Permissions, registry and actor mapping

### Actor mapping: incomplete and blocking

| Conceptual actor | Verified platform fact | Binding status |
|---|---|---|
| Student | Basic `student` role exists; use that acting role plus authoritative course registration. | Basic-role mapping available; membership API missing. |
| Faculty | `faculty` is a basic role per the platform RBAC model; course teaching assignment is an independent scope check. | Basic-role mapping available; assignment API missing. |
| TA | No TA/Teaching Assistant designation was present in the inspected synthetic catalogue. A Student basic role alone does not grant TA powers. | BPR-002: obtain approved real designation/expressible acting-role model; no invented alias. |
| Observer | No Observer designation was present in that catalogue. `Auditor` or another similarly named office is not assumed to mean LMS Observer. | BPR-002: obtain approved designation and authoritative section linkage. |
| System | Scheduled automatic actor, not a human IAM designation. | System-only permission, never granted to a person. |

The following is proposed registry data. The TA/Observer bundles deliberately remain unbound; this is not final deployable `registry.py` and cannot pass approval as a complete four-role grant map until BPR-002 closes.

```python
MODULE = {
    "code": "lms", "label": "LMS", "icon": "BookOpen",
    "base_path": "/lms", "nav_section": "Academics",
    "sort_order": 20, "status": "active",
}

PERMISSIONS = [
    ("lms.course.view", "View associated course workspaces"),
    ("lms.course.update", "Configure assigned course details"),
    ("lms.course_policy.view", "View the effective course policy"),
    ("lms.course_policy.update", "Version the course announcement policy"),
    ("lms.section.create", "Create course material sections"),
    ("lms.section.update", "Organize course material sections"),
    ("lms.material.view", "View course materials in visible scope"),
    ("lms.material.create", "Add course materials"),
    ("lms.material.update", "Edit and organize course materials"),
    ("lms.material.publish", "Publish and schedule course materials"),
    ("lms.assignment.view", "View visible course assignments"),
    ("lms.assignment.create", "Create course assignments"),
    ("lms.assignment.update", "Edit course assignments"),
    ("lms.assignment.publish", "Publish and schedule assignments"),
    ("lms.announcement.view", "Read course announcements"),
    ("lms.announcement.create", "Post course announcements"),
    ("lms.submission.view", "Read submissions within actor scope"),
    ("lms.submission.create", "Submit one's assignment work"),
    ("lms.grade.view", "Read grades within actor scope"),
    ("lms.grade.create", "Record a draft evaluation"),
    ("lms.grade.update", "Edit an evaluation within actor authority"),
    ("lms.grade.publish", "Release grades to students"),
    ("lms.content.publish", "System release of due scheduled content"),
]

SYSTEM_PERMISSIONS = ["lms.content.publish"]
SCOPE_PERMISSIONS = ("lms.course.view",)

_COMMON = ["lms.course.view", "lms.material.view", "lms.announcement.view"]
_STUDENT = [*_COMMON, "lms.assignment.view", "lms.submission.view",
            "lms.submission.create", "lms.grade.view"]
_FACULTY = [code for code, _ in PERMISSIONS if code not in SYSTEM_PERMISSIONS]
_TA = [*_COMMON, "lms.assignment.view", "lms.announcement.create",
       "lms.submission.view", "lms.grade.view", "lms.grade.create", "lms.grade.update"]
_OBSERVER = [*_COMMON]

ROLE_GRANTS = {"student": _STUDENT, "faculty": _FACULTY}
# No TA/Observer keys are invented. Bind _TA/_OBSERVER only after BPR-002.

NAV_ITEMS = [
    {"code": "lms.courses", "label": "Courses", "icon": "BookOpen",
     "to": "/lms/courses", "required_permission": "lms.course.view", "sort_order": 10},
    {"code": "lms.teaching", "label": "Teaching", "icon": "PencilSimple",
     "to": "/lms/teaching", "required_permission": "lms.course.update", "sort_order": 20},
    {"code": "lms.grading", "label": "Grading", "icon": "Exam",
     "to": "/lms/grading", "required_permission": "lms.grade.update", "sort_order": 30},
]
```

Every permission uses the `lms` prefix, a singular resource, and an allowed verb. No person receives `lms.content.publish`. The scope permission is not an alternate global grant: it does not encode a course ID, confer cross-course access or replace authoritative row scoping. The TA announcement permission exposes the action only at the role layer; D-02's current per-course flag still gates each write. A TA's `grade.update` never confers released-grade editing; D-06's actor/state guard refuses it.

The proposed nav routes are the only top-level module pages. Course detail, material/assignment editing, submission and released-grade views open inside these pages using a scoped selection/drawer rather than unregistered per-record routes. Every page implements loading, error, empty, forbidden and success states. Existing shell, profile, bell, sidebar and role switcher are reused rather than duplicated.

## 3.5 — Endpoint list and client integration

All paths below are relative to `/api/v1/lms/`. Every endpoint has `IsAuthenticatedPrincipal`, `HasModuleGrant("lms")` and the listed `HasPermission` check. Services then require the correct acting course role and scoped related IDs; read selectors start from `selectors/scoping.py`. A permission allows a verb, not every row. No Student/Observer serializer includes hidden grading/submission fields.

| Method and relative path | Required permission | Scope, response and source obligations |
|---|---|---|
| `GET courses/` | `lms.course.view` | Only authoritatively associated offerings/workspaces; batched IAM enrichment; CFR-LMS-001 and its AFRs, BR-LMS-001, BR-LMS-002, UC-LMS-001. |
| `GET courses/{workspace_id}/` | `lms.course.view` | Scoped syllabus, schedule, instructor/TA display; no Student roster; UC-LMS-001. |
| `PATCH courses/{workspace_id}/` | `lms.course.update` | Assigned Faculty edits/publishes LMS-owned details; UC-LMS-002. |
| `GET courses/{workspace_id}/policy/` | `lms.course_policy.view` | Assigned Faculty reads current TA-announcement flag/version; D-02. |
| `POST courses/{workspace_id}/policy-versions/` | `lms.course_policy.update` | Assigned Faculty appends effective-dated version; no update of old rows; D-02. |
| `POST courses/{workspace_id}/sections/` | `lms.section.create` | Assigned Faculty creates module/week section; UC-LMS-003. |
| `PATCH sections/{section_id}/` | `lms.section.update` | Scoped Faculty organization; validate same-course references; UC-LMS-003. |
| `GET courses/{workspace_id}/materials/` | `lms.material.view` | Audience-specific list; non-Faculty gets Published only; UC-LMS-004. |
| `POST courses/{workspace_id}/materials/` | `lms.material.create` | Faculty creates FILE/LINK/NOTE material; multipart only for FILE; UC-LMS-003; file path blocked by BPR-005. |
| `GET materials/{material_id}/` | `lms.material.view` | Scoped visible material DTO, no storage key; UC-LMS-004. |
| `PATCH materials/{material_id}/` | `lms.material.update` | Faculty edits/reorganizes; source-policy validation before any state effect; UC-LMS-003. |
| `POST materials/{material_id}/publish/` | `lms.material.publish` | Explicit immediate/scheduled transition; UC-LMS-003, BW-LMS-01. |
| `POST materials/{material_id}/withdraw/` | `lms.material.publish` | Faculty withdraws scheduled material; UC-LMS-015 alternative. This draft does not invent a Published-material withdrawal path. |
| `GET materials/{material_id}/download/` | `lms.material.view` | Scoped FILE stream through core/files; no unauthenticated blob URL; UC-LMS-004. |
| `GET courses/{workspace_id}/announcements/` | `lms.announcement.view` | Course-scoped content and timestamps; all four authorized audiences; UC-LMS-006. |
| `POST courses/{workspace_id}/announcements/` | `lms.announcement.create` | Assigned Faculty or assigned TA when current policy flag true; server author/time; UC-LMS-005, D-02/D-03. |
| `GET courses/{workspace_id}/assignments/` | `lms.assignment.view` | Student list contains Available only; Faculty/TA operational view is course-scoped; UC-LMS-009. |
| `POST courses/{workspace_id}/assignments/` | `lms.assignment.create` | Faculty creates a configured Draft; UC-LMS-007. |
| `GET assignments/{assignment_id}/` | `lms.assignment.view` | Scoped DTO with due date, instructions, submission kind and points possible; UC-LMS-009. |
| `PATCH assignments/{assignment_id}/` | `lms.assignment.update` | Faculty edits an allowed assignment state; do not invent post-publication edit effects; Q-04. |
| `POST assignments/{assignment_id}/publish/` | `lms.assignment.publish` | Faculty publishes immediate or scheduled; invalid draft refused; UC-LMS-008. |
| `POST assignments/{assignment_id}/withdraw/` | `lms.assignment.publish` | Faculty unpublishes a not-yet-released scheduled item; UC-LMS-015 alternative. |
| `GET assignments/{assignment_id}/download/` | `lms.assignment.view` | Download released instructions/configuration as a plain UTF-8 document; no new PDF dependency; UC-LMS-009. |
| `POST assignments/{assignment_id}/submissions/` | `lms.submission.create` | Registered Student, own server-derived owner, one correct-type submission; 201 on creation; UC-LMS-010, D-01/D-05. |
| `GET assignments/{assignment_id}/submissions/` | `lms.submission.view` | Student: own history/status only. Assigned Faculty/TA: grading-scope records. Observer: permission refusal; UC-LMS-011, UC-LMS-012, BR-LMS-014. |
| `GET submissions/{submission_id}/` | `lms.submission.view` | Student own or assigned grader scope; another Student's row is 404; UC-LMS-011, UC-LMS-012. |
| `GET submissions/{submission_id}/download/` | `lms.submission.view` | Same scope; FILE only; authorized parent checked before streaming. |
| `POST submissions/{submission_id}/grade/` | `lms.grade.create` | Faculty/TA creates Draft evaluation and audit attribution; UC-LMS-012. |
| `PATCH submissions/{submission_id}/grade/` | `lms.grade.update` | Faculty/TA Draft edit; released edit Faculty only, remains Released with D-06 synchronous before/after audit. |
| `POST submissions/{submission_id}/grade/release/` | `lms.grade.publish` | Faculty-only release; TA denied; UC-LMS-013. |
| `GET courses/{workspace_id}/grades/` | `lms.grade.view` | Student: own Released values only; Faculty/TA: scoped grading view. No Observer access; UC-LMS-014. |

No registration/add-drop/waitlist, examination totals, grade-sheet, plagiarism, discussion, rubric, group-assignment, chat or live-class endpoints are introduced. No public scheduler-trigger endpoint is introduced; System calls the services through Celery.

### Refusal and serialization contract

Use the existing error envelope with code, message, details and request ID. The ruling adopts 400 for malformed payloads and missing structurally required fields, 401 for absent/invalid authentication, 403 for missing verb/role authority, 404 for outside-scope/nonexistent resources, 409 for state/duplicate conflicts and 422 for semantic or business-rule failures. Distinguish omitted required fields from a syntactically present but semantically invalid configuration.

Late submissions use `SUBMISSION_DUE_DATE_EXCEEDED`; duplicate successful submissions use `SUBMISSION_ALREADY_EXISTS`. Evaluate scope before using arbitrary body IDs and keep all failure paths free of business-state changes. Cookie-authenticated unsafe methods retain the platform CSRF check and principal-aware throttle. Do not widen the existing authentication/permission classes.

The client sends explicit declared fields, never owner IDs, timestamps, status, grading attribution, audit rows or storage paths. Server-owned fields are read-only. Parse/query failures have documented 400/422 categories. Lists use existing pagination/filter conventions, `select_related`/`prefetch_related` and bounded batch enrichment; query-budget tests compare two and twenty rows.

### Client routes and shell instruction

| Client route | Guard | Contents |
|---|---|---|
| `/lms/courses` | `RequirePermission("lms.course.view")` after module grant | Associated-course selection; audience-specific course workspace. Student owns submission/grade views; Observer sees only permitted common content. |
| `/lms/teaching` | `RequirePermission("lms.course.update")` | Assigned Faculty details, materials, announcements, assignments, course policy and grade-release controls. |
| `/lms/grading` | `RequirePermission("lms.grade.update")` | Assigned Faculty/TA grading; render release/released-edit controls only with actual Faculty authority. Server guards remain authoritative. |

Planned `MODULE_REGISTRY` entry in this repository:

```ts
lms: { code: "lms", basePath: "/lms", load: () => import("../modules/lms/routes") }
```

Instruction for the full shell owner (not performed in module-only): add this entry to `Fusion-client`'s `INTEGRATED_MODULES`, then verify its established icon/route contract:

```js
{ id: "lms", label: "LMS", icon: "BookOpen", to: "/lms/courses", section: "Academics" }
```

IAM seeding makes the module grantable and publishes its per-role nav; it does not replace this separate full-shell entry. The isolated client's module must also render correctly when framed with `?embed=1`. A direct route visit by the wrong role must show the existing Forbidden behavior rather than loading an unauthorized page.

## 3.6 — Contracts and shared boundaries

### Required external read contract — unavailable

These are required capabilities for the platform owner to supply, not invented endpoint paths or `IamClient` signatures:

1. Batch retrieval/listing of stable course offerings with term/section identity and course-home display information.
2. The authenticated principal's authoritative offering-specific Student registration, Faculty assignment, TA assignment and D-04 Observer linkage, with acting-role interpretation and validity/revocation semantics.
3. Batch enrichment of instructor/TA user IDs through the already supported user-directory operation; avoid per-row requests.
4. Defined authentication, pagination, absent/missing associations, upstream unavailability, stale/revoked membership handling and supported source revision.

BPR-001 closes only when a real supported contract is identified or delivered on official IAM main. A fake client endpoint and tests against fabricated memberships are not substitutes. Do not query or write the ERP from LMS. On unavailable/unverifiable associations, do not expose the workspace or authorize a write. The precise outage status and error code must follow the owner/platform contract; they are not guessed here. Do not authorize from a stale local editable membership cache.

### Planned LMS exports

No supplied requirement names a consuming module or asks LMS to publish grades to Examination. Therefore the initial `contracts.py` has no invented cross-module grade export or registration API. If a supported consumer is subsequently identified, expose only an approved minimal DTO through a plural getter accepting a sequence of IDs; do not let the caller import models, selectors or services. This choice satisfies the plural-getter rule without introducing an unused singular API.

### File capability drift — BPR-005

PS §§3.2/3.5, AFR-LMS-003.1/008.1 and UC-LMS-003/010 require genuine file content in addition to link/text variants. Current `core/files/validators.py` sanitizes names only, and `core/files/storage.py` is explicitly read-only legacy storage. The Drive-link parser cannot stand in for a file-upload implementation without an approved specification change.

Proposed additional shared change for explicit approval: extend `core/files` with a module-neutral validated byte-upload writer, content-based media/type and configured-size checks, opaque storage keys, private roots and authorized parent downloads. Keep LMS metadata/ownership in the module; keep `core` independent of `modules` and `fusion_auth`. Preserve Placement's current read-only/Drive behavior. Specify accepted file types, size limits and root configuration before implementation; no new dependency is approved or selected by this draft. An approved supported external upload service is an alternative only if it preserves the genuine FILE semantics and its contract is supplied.

### Planned shared registration changes

Use only the builder prompt's preapproved registration changes for app, URL, client module registry, lint-layer declarations, Celery schedule merge, test accounts, and generated schema/permission manifest. Add the one-line shell integration instruction for its owner. Any IAM client addition, `core/files` implementation, dependency, extra test-harness edit or change outside those preapproved registrations requires a separate approval record. The generated manifest is produced by `make permissions` and applied by the IAM's existing seeding command; it is not a local editable RBAC database.

## 3.7 — Scheduled work

| Task / beat entry | Planned cadence and trigger | Guards, repeated-run behavior and failure effect |
|---|---|---|
| `lms.release_due_materials` / `lms.release-due-materials` | Proposed 15-second bounded catch-up scan; request an ETA execution after a committed scheduling change where the existing broker contract permits it. | Only still-SCHEDULED, valid, due materials. Lock/re-read each candidate and use the ordinary material transition service. Early, withdrawn, repeated or competing runs create no extra transition/audit. Worker failure leaves content unavailable and records operational failure, per UC-LMS-015. |
| `lms.release_due_assignments` / `lms.release-due-assignments` | Same proposed cadence and post-commit due-time dispatch strategy. | Only still-SCHEDULED assignments whose release condition is met. Same transactional choke point; no duplicate publication. Failure keeps content unavailable and is recorded. |

`BEAT_SCHEDULE` and `TASK_ROUTES` are exported from the module's `schedule.py` and merged through `config/celery.py`; human roles never hold the system release permission. Use bounded batches and record IDs/counts/failures, not bodies or personal names. No Student request invokes the System permission. Selectors remain reads; they do not secretly publish content during GET.

The exact cadence/queue and ETA-dispatch failure path are design proposals for blueprint approval, not source-mandated timing numbers. Normal release is triggered at the configured timestamp by the worker; recovery scans catch missed dispatches. Operational latency and worker/beat availability must be documented; if timing cannot meet the required interpretation, record a gap instead of pretending immediate release during an outage. Both tasks must pass sequential double-run and concurrent double-run tests.

D-03 requires no notification delivery task, outbox mailer, push/SMS integration or new notification UI. D-01 validates deadlines at submission time; no invented expiry task or CLOSED assignment state is needed. D-05 uses successful-row uniqueness, not an attempt-reset timer.

Deployment sequence: approved dependencies/configuration → migrations → idempotent baseline policy seed → module registration → generated manifest and IAM permission seed → readiness → worker and beat → API/client. A fresh database must support first use without manual ORM work. The environment baseline's existing Placement worker configuration is not proof that LMS tasks or readiness have been implemented.

## 3.8 — Open questions, approvals and readiness

### Adoption record

D-01 through D-06 are recorded as adopted in the supplied formal ruling, with exact evidence hash in the header. They close the six policy-choice proposals at the pair level. They do not approve this blueprint, supply IAM endpoints, provision missing designations, authorize a shared file writer, or establish an implementation score.

| Open item | Required closure before implementation / final approval |
|---|---|
| BPR-001 — Course-association contract | Real supported owner contract and official source revision; offering keys, all four associations, display metadata, batch semantics, revocations and failure behavior. No local authority/fake endpoint workaround. |
| BPR-002 — Actors and identifiers | Instructor confirmation of code/docs number; real TA/Observer designation mapping or an explicitly approved platform-supported alternative. Pair endorsement alone does not establish instructor assignment or role availability. |
| BPR-004 — Exact blueprint approval | Complete the remaining blocked design details, identify this version/hash or the student's documentation commit, and obtain the actual approver's dated written decision. No approval is represented by this draft. |
| BPR-005 — Genuine file support | Approve the specified shared-kernel extension or supply a supported equivalent contract; settle file profile/limits/root and separately approve any new dependency. |
| Q-04 — Assignment edit effects not settled by v1.0 | Confirm whether already-available assignments may be edited and what happens to existing submissions. Scheduled withdrawal before release is explicitly supported. Material edits preserve the current publication state unless a separately supported scheduling operation is selected; Published-material withdrawal is not added. Do not invent a CLOSED lifecycle or silently change due dates after submissions. |
| Q-05 — Timing and publication behavior | Approve task cadence/queue, due-time dispatch and failure/recovery behavior consistent with UC-LMS-015, including observable scheduling latency. |

The formal ruling says 400 for omitted required request fields and 422 for semantic failures; the API section preserves that distinction. D-01's inclusive exact deadline is recorded as an adopted clarification to the source's general “before due date” language. Old/new score/feedback audit fields and Faculty-only retained-Released edits are D-06 additions, not requirements falsely attributed to unchanged BR-LMS-019 alone.

### Planned validation and review handoff

After prerequisites and blueprint approval, implement bottom-up using module-local `domain/`, `models/`, `selectors/`, `services/`, `api/`, registry and schedules, followed by client pages. Every live UC must have an HTTP-level journey with its explicit success/alternative/exception obligations, with exact source IDs. Include D-01 equality/before/after clocks, D-05 rejected-versus-successful attempt consumption and concurrent duplicates, D-06 rollback/attribution/released visibility, all actor/scope refusals, scheduled withdrawal/failure/repeated/concurrent runs and query budgets. These are planned builder checks, not completed Student 2 frozen designs.

Run the exact gates in the current official builder/review prompt, including backend/client/browser checks, real PostgreSQL and required coverage, controlled mutation checks, deployment readiness and fresh-database behavior. Record every actual review output and round; do not assign a 10/10 score here. Students perform any commit/push/PR actions themselves under the assignment's rules. No publishing is authorized by this document.

Student 2's official spec-only design/automation process starts at its required milestone and uses fresh contexts plus only its permitted source artifacts. The original specifications remain unchanged; policy clarifications and their provenance remain distinguishable. No preliminary test, score or different assignment's implementation is backdated into that sequence.

**Current conclusion:** all 103 specification IDs have a planned design location, but this version is not ready for implementation approval while its upstream, role and file-support dependencies remain unresolved.
