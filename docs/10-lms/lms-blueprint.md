# LMS (Course Management) blueprint

**Version:** A9-LMS-BP-0.3 — implementation-aligned record, 23 November 2026 (IST).

**Branch:** `module/lms`. **Module:** `lms`. **Documentation:** `docs/10-lms/`.

**Platform base:** `5595be6628b4cdc6f8b47cf74bac267a2470f780`.

**Design approval basis:** A9-LMS-BP-0.2 at documentation commit
`fca2636c8b92c9312acbfa25d59c4fd636b47ba9`, approved in writing by paired
approver Vedha on 22 November 2026. Its original blueprint SHA-256 is
`f053725ae7f6b25b1e8e8c457c176209f9b954e562c1783c318512d9eb8c5d39`.
This revision records the implemented architecture and Round 2 corrections; it is
not represented as a new human approval of a changed specification. D-01–D-06,
F-03, F-04 and F-05 remain the adopted policies. The stored policy version remains
`A9-LMS-BP-0.2`.

**Verified IAM prerequisite:** `494160849bd101a5cb77a1b1c9f0881307079888` on
local IAM main, parent `d143e4e61b11a2a5e21c03355f8b784d83103b5d`.
No official upstream merge or production teaching adapter is claimed.

**Status:** Stage B is implemented. Builder verification is recorded in
[lms-quality-report.md](lms-quality-report.md). Round 2 reviewed `92b4ed5` and
returned 17 findings; this revision records their corrections. A completed
independent review after the corrections remains outstanding. Step 8 stays on hold.

The six original LMS v1.0 specification artifacts define the 103 live obligations
below. [policy-decisions.md](policy-decisions.md) distinguishes later rulings from
the unchanged source. Preliminary partner test designs are not design authority.
The module/folder identifiers are pair-endorsed working values; no separate
instructor confirmation is claimed. Shared approval is preserved in
[Shared_Changes_Approval_Decision.md](Shared_Changes_Approval_Decision.md).

## 3.1 — Traceability table

All 103 live IDs appear once: 15 CFRs, 47 AFRs, 19 BRs, 15 UCs, five BWs and two CWs.
No retired IDs were identified. The reference command resolves exact source/test
line links from this inventory: `.venv/bin/python ops/docs/lms_reference.py`.

| ID | Source obligation | Layers | Actual enforcement | Policy / verification |
|---|---|---|---|---|
| CFR-LMS-001 | The system shall provide a dedicated course workspace for each course and allow an authorized course user to open that workspace and view the course home information for the specific course to which the user is enrolled in, assigned to, or otherwise linked. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-002 | The system shall allow Faculty to own/configure the workspace for assigned courses and to publish and edit the course details presented in that workspace. | services | `modules/lms/services/workspaces.py::update_details` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-003 | The system shall allow Faculty to upload course materials as files, links, or notes, organize them into modules or weekly sections, and optionally schedule a future release date. | services | `modules/lms/services/materials.py::save_material` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-004 | The system shall provide Students, TAs, and Observers with read-only access to published course materials for courses they are authorized to access. | selectors | `modules/lms/selectors/scoping.py::materials` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-005 | The system shall allow Faculty, and TAs where permitted, to post timestamped course-wide announcements and shall make posted announcements visible to all users enrolled in or linked to the course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-006 | The system shall allow Faculty to create and edit an assignment for an assigned course, capturing due date, instructions, submission type, and points possible, with the assignment remaining in Draft state before publication. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-007 | The system shall allow Faculty to publish an assignment and shall control Student visibility according to the configured release date; Students shall be able to view and download assignments once released. | services | `modules/lms/services/releases.py::change_release` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-008 | The system shall allow a Student to submit assignment work using the submission type configured by Faculty and shall support the baseline on-time submission case before the due date. | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-009 | The system shall allow a Student to view only the Student’s own assignment submission history and submission status, including submitted, late, or missing where applicable. | selectors | `modules/lms/selectors/scoping.py::submissions` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-010 | The system shall allow Faculty and TAs to grade individual submissions by entering points and feedback, and shall attribute each grading action to the person who performed it. | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-011 | The system shall keep grades and feedback in Draft state until Faculty releases them, shall prevent Students from seeing draft grades, and shall make released grades/feedback available to the applicable Student. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-012 | The system shall allow a Student to view the Student’s own released grade and feedback in read-only form. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-013 | Whenever a released grade is changed, the system shall log the change and record who made the change and when it was made. | services | `modules/lms/services/grading.py::GradeAuditLog.objects.create` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-014 | The system shall provide TAs with course viewing, submission-viewing and grading capabilities for assigned courses, while preventing TAs from creating or editing assignments, materials, or course structure; announcement posting is allowed only where permitted. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CFR-LMS-015 | The system shall provide an Observer with read-only access to course details, published materials, and announcements for the linked course while preventing access to individual submissions, grades, and other Student-specific data and preventing all write actions. | registry.py | `modules/lms/registry.py::"lms_observer":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-001.1 | The system shall open a dedicated course workspace when a user selects a course for which the user has authorized course access. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-001.2 | The system shall display the course syllabus, schedule, instructor(s), and TA(s) on the course home page. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-001.3 | The system shall restrict a course workspace to users enrolled in, assigned to, or linked to that specific course. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-002.1 | The system shall allow Faculty to configure the course workspace for courses assigned to that Faculty member. | services | `modules/lms/services/workspaces.py::update_details` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-002.2 | The system shall allow Faculty to publish and edit course details for an assigned course workspace. | services | `modules/lms/services/workspaces.py::update_details` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-003.1 | The system shall allow Faculty to add course materials as files, links, or notes. | services | `modules/lms/services/materials.py::save_material` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-003.2 | The system shall allow Faculty to organize course materials into modules or weekly sections. | services | `modules/lms/services/materials.py::save_material` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-003.3 | The system shall allow Faculty to configure a future release date for course material. | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-003.4 | When a scheduled material release time is reached, the system shall make that material published/available to authorized course users. | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-004.1 | The system shall allow a Student to view published course materials for the Student’s registered course in read-only form. | selectors | `modules/lms/selectors/scoping.py::materials` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-004.2 | The system shall allow a TA to view published course materials for the assigned course in read-only form. | selectors | `modules/lms/selectors/scoping.py::materials` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-004.3 | The system shall allow an Observer to view published course materials for the linked course in read-only form. | selectors | `modules/lms/selectors/scoping.py::materials` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-005.1 | The system shall allow Faculty to post a course-wide announcement for an assigned course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-005.2 | The system shall allow a TA to post a course-wide announcement only where the TA is permitted to do so for that course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-005.3 | The system shall timestamp each posted course announcement. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-005.4 | The system shall make a posted course announcement visible to all users enrolled in or linked to that course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-006.1 | The system shall allow Faculty to create an assignment for an assigned course. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-006.2 | The system shall capture an assignment due date, instructions, submission type, and points possible. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-006.3 | The system shall allow Faculty to edit an assignment. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-006.4 | The system shall keep an assignment in Draft state until Faculty publishes it. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-007.1 | The system shall allow Faculty to publish an assignment. | services | `modules/lms/services/releases.py::change_release` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-007.2 | The system shall withhold a published assignment from Students until its configured release date/time. | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-007.3 | When the configured assignment release time is reached, the system shall make the assignment available to authorized Students. | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-007.4 | The system shall allow a Student to view and download an assignment after it has been released for the Student’s registered course. | services | `modules/lms/services/releases.py::change_release` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-008.1 | The system shall allow a Student to submit assignment work as a file, text, or link according to the assignment’s configured submission type. | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-008.2 | The system shall accept and record a Student submission made before the assignment due date. | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-009.1 | The system shall allow a Student to view the Student’s own submission history for an assignment. | selectors | `modules/lms/selectors/scoping.py::submissions` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-009.2 | The system shall show the Student’s own submission status as submitted, late, or missing where applicable. | selectors | `modules/lms/selectors/scoping.py::submissions` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-010.1 | The system shall allow Faculty to grade an individual Student submission by entering points and feedback. | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-010.2 | The system shall allow a TA to grade an individual Student submission for the assigned course by entering points and feedback. | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-010.3 | The system shall record the identity of the Faculty member or TA who performs a grading action. | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-011.1 | The system shall keep a grade and feedback in Draft state until release. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-011.2 | The system shall prevent a Student from viewing a grade or feedback before it is released. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-011.3 | The system shall allow Faculty to release draft grades and feedback to Students. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-012.1 | The system shall allow a Student to view the Student’s own grade and feedback after release. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-012.2 | The system shall present released grade and feedback to the Student in read-only form. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-013.1 | When a released grade is changed, the system shall record who made the change. | services | `modules/lms/services/grading.py::GradeAuditLog.objects.create` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-013.2 | When a released grade is changed, the system shall record when the change was made. | services | `modules/lms/services/grading.py::GradeAuditLog.objects.create` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-014.1 | The system shall allow a TA to view course details, published materials, and announcements for the assigned course. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-014.2 | The system shall allow a TA to view Student submissions for the assigned course. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-014.3 | The system shall prevent a TA from creating or editing assignments. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-014.4 | The system shall prevent a TA from creating or editing course materials. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-014.5 | The system shall prevent a TA from modifying course structure. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-015.1 | The system shall allow an Observer to view course details, published materials, and announcements for the linked course in read-only form. | registry.py | `modules/lms/registry.py::"lms_observer":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-015.2 | The system shall prevent an Observer from viewing individual Student submissions. | registry.py | `modules/lms/registry.py::"lms_observer":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-015.3 | The system shall prevent an Observer from viewing grades or any other Student-specific data. | registry.py | `modules/lms/registry.py::"lms_observer":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| AFR-LMS-015.4 | The system shall prevent an Observer from performing write actions anywhere in the LMS Course Management module. | registry.py | `modules/lms/registry.py::"lms_observer":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-001 | A user may access a course workspace only for a course in which the user is enrolled, assigned, or otherwise linked. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-002 | Student course access shall be based on the existing Fusion course-registration data; this module shall not redefine registration/add-drop/waitlist rules. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-003 | An Observer may read course details, published materials, and announcements for the linked course, but may not view individual submissions, grades, or other Student-specific data and may not perform any write action. | registry.py | `modules/lms/registry.py::"lms_observer":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-004 | A TA may view permitted course content, view submissions, grade, and post announcements where permitted, but may not create/edit assignments, materials, or course structure. | registry.py | `modules/lms/registry.py::"lms_ta":` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-005 | Students, TAs, and Observers may view course materials only after those materials are published/released for the course. | selectors | `modules/lms/selectors/scoping.py::materials` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-006 | A course material configured with a future release date shall remain unavailable until that release date/time is reached. | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-007 | Faculty may post course announcements; a TA may post only where permitted by Faculty for that course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-008 | Each posted announcement shall be timestamped and visible to all users enrolled in or linked to the course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-009 | An assignment must define due date, instructions, submission type, and points possible before publication. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-010 | An assignment shall remain in Draft state before Faculty publishes it. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-011 | A published assignment shall become visible to Students only when its configured release date/time condition is satisfied. | services | `modules/lms/services/releases.py::change_release` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-012 | A Student submission must use the submission type configured for the assignment: file, text, or link. | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-013 | The current baseline explicitly supports Student submission before the due date; late-submission behavior is unresolved and shall not be invented. | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-014 | A Student may view only the Student’s own submission history and status. | selectors | `modules/lms/selectors/scoping.py::submissions` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-015 | Faculty and TAs may grade individual submissions for the applicable course, and each grading action shall be attributed to the person who performed it. | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-016 | Grades and feedback shall remain Draft and invisible to Students until released. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-017 | Under the current baseline, Faculty releases grades and feedback to Students; TA grading does not by itself release grades. | services | `modules/lms/services/grading.py::release_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-018 | After release, a Student may view the Student’s own grade and feedback in read-only form. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BR-LMS-019 | Whenever a released grade is changed, the system shall log the change, recording who made it and when. | services | `modules/lms/services/grading.py::GradeAuditLog.objects.create` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-001 | Access Course Workspace: Open the dedicated workspace for a course the user is authorized to access and view course-home information. | selectors | `modules/lms/selectors/scoping.py::resolve_scope` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-002 | Manage Course Details: Configure the assigned course workspace and publish/edit course details. | services | `modules/lms/services/workspaces.py::update_details` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-003 | Manage Course Materials: Add and organize course materials and optionally schedule their release. | services | `modules/lms/services/materials.py::save_material` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-004 | View Published Course Materials: View published course materials for an authorized course. | selectors | `modules/lms/selectors/scoping.py::materials` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-005 | Post Course Announcement: Post a course-wide announcement. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-006 | View Course Announcements: Read course-wide announcements for an authorized course. | services | `modules/lms/services/announcements.py::post_announcement` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-007 | Create or Edit Assignment: Create or edit an assignment and maintain it in Draft state until publication. | services | `modules/lms/services/assignments.py::save_assignment` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-008 | Publish Assignment: Publish a Draft assignment and establish its release timing. | services | `modules/lms/services/releases.py::change_release` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-009 | View or Download Published Assignment: View/download an assignment after it is released. | services | `modules/lms/services/releases.py::change_release` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-010 | Submit Assignment: Submit assignment work using the configured submission type. | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-011 | View Submission History and Status: View own assignment submission history and status. | selectors | `modules/lms/selectors/scoping.py::submissions` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-012 | Grade Submission: Grade an individual Student submission by recording points and feedback. | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-013 | Release Grades and Feedback: Release draft grades/feedback to Students. | services | `modules/lms/services/grading.py::release_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-014 | View Released Grade and Feedback: View own released grade and feedback in read-only form. | selectors | `modules/lms/selectors/scoping.py::grades` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| UC-LMS-015 | Process Scheduled Content Release: Make scheduled course material or an assignment available when its configured release time is reached. | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BW-LMS-01 | Scheduled Course Material Release | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BW-LMS-02 | Assignment Immediate Release and On-Time Submission | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BW-LMS-03 | Assignment Scheduled Release and On-Time Submission | services | `modules/lms/services/releases.py::transition_content` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BW-LMS-04 | Faculty Grading and Grade Release | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| BW-LMS-05 | TA Grading and Faculty Grade Release | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CW-LMS-01 | Assignment Publication and Submission | services | `modules/lms/services/submissions.py::create_submission` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |
| CW-LMS-02 | Grading and Grade Release | services | `modules/lms/services/grading.py::save_grade` | [Enforcement and builder assertion](lms-reference.md); D-01–D-06 remain unchanged. |

## 3.2 — Domain model and constraints

Models use internal integer primary keys, plain integer IAM user references and
only module-local protected foreign keys. `CourseWorkspace.external_offering_key`
is a unique 68-character `cof_<sha256>` value from IAM. LMS does not own enrollment
or an editable teaching-assignment authority.

| Aggregate file | Models and invariants |
|---|---|
| `models/workspaces.py` | CourseWorkspace: unique offering key, LMS syllabus/schedule and publication/configuring actor. CoursePolicyVersion: unique workspace/version and workspace/effective-time; effective-dated append-only policies, safe default false. |
| `models/materials.py` | MaterialSection: MODULE/WEEK, nonnegative order. Material: FILE/NOTE/LINK, exclusive payload, scoped section, DRAFT/SCHEDULED/PUBLISHED, required scheduled time; named listing/due-scan indexes. |
| `models/announcements.py` | Announcement: course-scoped text, immutable author and server creation time. No outbound notification channel. |
| `models/assignments.py` | Assignment: optional title, required instructions/due/type/points; FILE/TEXT/LINK, nonnegative points; DRAFT/SCHEDULED/AVAILABLE; scheduled-time check and named due index. |
| `models/submissions.py` | Submission: local assignment, server owner/time, exclusive file/text/link payload, policy version; unique assignment/user is the concurrent one-success invariant. |
| `models/grading.py` | Grade: one-to-one submission, nonnegative points, DRAFT/RELEASED and required release actor/time. GradeAuditLog: immutable old/new points, feedback and states with actor/time. |
| `models/transitions.py` | ContentTransitionLog: exactly one material/assignment subject, event, old/new state and release time, actor role/user (null user for System), timestamp. Append-only and transactionally inseparable from lifecycle writes. |
| `models/files.py` | StoredFile: validated private bytes metadata and opaque storage key, workspace/owner; keys never appear in response DTOs. |
| `models/base.py` | Shared append-only queryset/model behavior and payload constraint builder. `models/__init__.py` only re-exports aggregates. |

`0001_initial` remains the initial business schema; `0002_contenttransitionlog`
adds persisted lifecycle audit without destroying existing content. Fresh setup
and rollback/reapply cover both migrations.

Transactional services enforce scope and domain rules before persistence:

- `workspaces.update_details`, `set_policy`, `save_section`: assigned Faculty;
  policy changes append under the workspace lock, preserving history.
- `assignments.save_assignment`: assignment-first lock; after submissions, type
  is immutable and due time may only stay equal or extend beyond recorded work;
  after grading, points possible is immutable. Forbidden edits return 422.
- `submissions.create_submission`: assignment-first lock, one authoritative aware
  UTC timestamp, availability/type/deadline checks; inclusive deadline, no late
  acceptance, one successful submission. Failed validation/storage consumes none.
  Database uniqueness backs the 409 duplicate refusal.
- `grading.save_grade`: assignment then submission/grade locks, role/state checks,
  grade plus immutable audit in one transaction. Faculty/TA draft grading does not
  publish. `grading.release_grade` enforces Faculty-only release; a Faculty
  correction of a Released grade retains Released and audits old/new values.
- `releases.transition_content`: the single atomic locked lifecycle writer for
  human publish/schedule/reschedule/withdraw and System release. It validates the
  declarative edge, updates state and writes ContentTransitionLog together. Missing,
  withdrawn, duplicate or not-yet-due System jobs have no state/audit side effects.

There is no spendable ledger or invented score cap. Domain code is framework-free;
services translate RuleViolation into shared API errors. Invariants expressible
in SQL remain named constraints, and actor/relationship rules stay in services.

## 3.3 — Declarative state machines


State/event/actor/target/guards are immutable transition data in `domain/state_machine.py`. The domain imports no Django, DRF, Celery, settings or `core.api` exceptions. Services translate plain domain exceptions to the shared API error classes. No default transition or permissive fallback exists.

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

Every API request requires authentication, `HasModuleGrant("lms")` and its exact
method permission. `selectors/scoping.resolve_scope` additionally reads current
IAM associations for the acting role: student→STUDENT, faculty→FACULTY,
lms_ta→TA, lms_observer→OBSERVER. Held roles are never unioned. Permissions alone
never bypass offering scope. System has no human designation or login.

The registry below is the actual declaration in `modules/lms/registry.py`:

```python
"""Real IAM designations and permissions for the acting role only."""

MODULE = {
    "code": "lms",
    "label": "Course Management",
    "icon": "BookOpen",
    "base_path": "/lms",
    "nav_section": "Learning",
    "sort_order": 20,
    "status": "active",
}
NAV_ITEMS = [
    {
        "code": "lms.courses",
        "label": "My Courses",
        "icon": "BookOpen",
        "to": "/lms/courses",
        "required_permission": "lms.course.view",
        "sort_order": 10,
    },
    {
        "code": "lms.teaching",
        "label": "Teaching",
        "icon": "PencilSimple",
        "to": "/lms/teaching",
        "required_permission": "lms.course.update",
        "sort_order": 20,
    },
    {
        "code": "lms.grading",
        "label": "Grading",
        "icon": "Exam",
        "to": "/lms/grading",
        "required_permission": "lms.grade.update",
        "sort_order": 30,
    },
]
PERMISSIONS = [
    (f"lms.{resource}.{action}", label)
    for resource, action, label in (
        ("course", "view", "Read linked course workspaces"),
        ("course", "update", "Configure assigned courses"),
        ("course_policy", "view", "Read course announcement policy"),
        ("course_policy", "update", "Append course policy versions"),
        ("section", "create", "Create material sections"),
        ("section", "update", "Organize material sections"),
        ("material", "view", "Read published materials"),
        ("material", "create", "Create course materials"),
        ("material", "update", "Edit course materials"),
        ("material", "publish", "Publish or schedule course materials"),
        ("assignment", "view", "Read available assignments"),
        ("assignment", "create", "Create assignments"),
        ("assignment", "update", "Edit assignments"),
        ("assignment", "publish", "Publish or schedule assignments"),
        ("announcement", "view", "Read course announcements"),
        ("announcement", "create", "Post course announcements"),
        ("submission", "view", "Read scoped submissions"),
        ("submission", "create", "Submit own assignment work"),
        ("grade", "view", "Read scoped grades and feedback"),
        ("grade", "create", "Record draft grades"),
        ("grade", "update", "Update scoped grades"),
        ("grade", "publish", "Release grades and feedback"),
        ("content", "publish", "System scheduled release"),
    )
]
SYSTEM_PERMISSIONS = ["lms.content.publish"]
_COMMON = ["lms.course.view", "lms.material.view", "lms.announcement.view"]
ROLE_GRANTS = {
    "student": [
        *_COMMON,
        "lms.assignment.view",
        "lms.submission.view",
        "lms.submission.create",
        "lms.grade.view",
    ],
    "faculty": [
        code
        for code, _ in PERMISSIONS
        if code not in (*SYSTEM_PERMISSIONS, "lms.submission.create")
    ],
    "lms_ta": [
        *_COMMON,
        "lms.assignment.view",
        "lms.announcement.create",
        "lms.submission.view",
        "lms.grade.view",
        "lms.grade.create",
        "lms.grade.update",
    ],
    "lms_observer": _COMMON,
}
SCOPE_PERMISSIONS = ("lms.course.view",)

```

Faculty owns structure/publication. The current course policy separately gates TA
announcements. TAs can grade Draft work, never release or correct Released grades.
Observers see common published material/details/announcements only, without
assignments or student-specific data. Students see only their submissions and
Released grades. All direct-resource lookups apply the same scoping.

## 3.5 — Endpoint list and client integration

All paths are under `/api/v1/lms/`. The committed OpenAPI contains exact DTOs and
examples for every operation. Endpoint-specific hooks use the shared HTTP/CSRF
client; list/detail cache keys include user ID and active role. Response interfaces
match nullable fields, enums, server author/times, release attribution and policy
version. No caller-provided owner/state/audit fields are accepted.

| Resource paths | Methods and permissions |
|---|---|
| `courses/`, `courses/{id}/` | GET course.view; detail PATCH course.update |
| `courses/{id}/policy/`, `courses/{id}/policy-versions/` | GET course_policy.view; POST course_policy.update |
| `courses/{id}/sections/`, `sections/{id}/` | POST section.create; PATCH section.update |
| `courses/{id}/materials/`, `materials/{id}/` | GET material.view; collection POST material.create; detail PATCH material.update |
| `materials/{id}/publish/`, `materials/{id}/withdraw/` | POST material.publish; withdraw applies only to Scheduled |
| `materials/{id}/download/` | GET material.view; parent-authorized private FILE stream |
| `courses/{id}/announcements/` | GET announcement.view; POST announcement.create plus role/policy |
| `courses/{id}/assignments/`, `assignments/{id}/` | GET assignment.view; collection POST assignment.create; detail PATCH assignment.update |
| `assignments/{id}/publish/`, `assignments/{id}/withdraw/` | POST assignment.publish; withdraw applies only to Scheduled |
| `assignments/{id}/download/` | GET assignment.view; UTF-8 instructions/configuration attachment |
| `assignments/{id}/submissions/`, `submissions/{id}/` | GET submission.view; collection POST submission.create |
| `submissions/{id}/download/` | GET submission.view; private FILE only |
| `submissions/{id}/grade/` | POST grade.create; PATCH grade.update |
| `submissions/{id}/grade/release/` | POST grade.publish plus Faculty-only release |
| `courses/{id}/grades/` | GET grade.view; own Released grades for Student |

There are 31 method/path operations across 23 view classes. Cursor lists default
to 25, maximum 100, with batched IAM enrichment and query-budget regressions.
Malformed/unknown body fields return 400, authentication 401, authority/CSRF 403,
missing/out-of-scope IDs 404, lifecycle/duplicate conflicts 409, semantic rules 422,
principal write throttling 429, IAM unavailability 503. Refusals preserve state.
Empty action bodies also reject undeclared keys. Late and duplicate submissions
have `SUBMISSION_DUE_DATE_EXCEEDED` and `SUBMISSION_ALREADY_EXISTS` codes.

| Client page | Guard and actual contents |
|---|---|
| `/lms/courses` | course.view: course selection, details, common materials/announcements; authorized assignments, own submission work/history and Released grades. |
| `/lms/teaching` | course.update: course details, effective TA policy, sections, material and assignment editing, immediate/scheduled/withdraw controls. |
| `/lms/grading` | grade.update: scoped submissions and draft grading; Faculty release and Released-grade correction controls. |

Every page uses the existing shell and loading/error/empty/forbidden/success
states. Restricted controls are tested on mounted pages as well as route guards.
The client registry loads `../modules/lms/routes` lazily at `/lms`.
Full-shell owner instruction (module-only scope): add
`{ id: "lms", label: "Course Management", icon: "BookOpen", to: "/lms/courses", section: "Learning" }`
to `Fusion-client`'s existing `INTEGRATED_MODULES`. That external shell file has
not been edited by this module submission.

## 3.6 — Contracts and shared boundaries

The pinned IAM service provides service-authenticated GET
`/api/iam/v1/academics/course-offerings` and
`/api/iam/v1/academics/course-associations`. Offerings accept offering keys and
bounded limit/offset; associations require user IDs and optionally exact offering
keys/course role. The wrappers fetch all pages, and fail closed on unavailable or
incomplete authorization. Keys are stable 68-character opaque `cof_<sha256>` values
over canonical source course/term context. LMS never imports ERP tables directly.

Stage A verified 341 PostgreSQL IAM tests, both live HTTP 200 contracts, real local
TA/Observer designations and 3,686 offering contexts. All 117,264 source registration
rows were preserved with ordered SHA-256
`3ff8b50a99ea1bd6c137cd685c3fbe95d8b830dda0bc7a8b69a93745f2c4e6e1`.
Student associations are actual synthetic ERP registrations; nonstudent bindings
are explicit revocable `synthetic_fixture` records, not a recovered production
teaching feed. A production teaching-source adapter is outside the local delivery.

`contracts.py` introduces no invented cross-module export. No consuming module or
Examination grade feed is specified. Person enrichment uses batched IAM projections;
there are no cross-module/user foreign keys or local access-control tables.

The approved shared `core/files/writers.py` implements private validated uploads
and attachment streaming without importing modules/auth. Its profiles accept
PDF/ZIP/TAR.GZ/TXT/DOCX/IPYNB with content/container validation and an extension
whitelist. Material cap: 25,000,000 bytes; submission cap: 10,000,000 bytes. No
archive extraction, notebook execution or public byte URL exists. Private storage
is outside the web/repository root; storage keys are opaque and filenames sanitized.
Staged files are removed on transaction failure. Existing legacy storage/Drive
parsing and Placement behavior remain compatible.

Shared registrations are settings, URL inclusion, Celery routing/schedule merge,
import-layer declaration, client registry, new demo browser accounts, OpenAPI and
permission manifest. IAM client/FakeIam projections and the writer are explicitly
approved Stage B scope. The 23 November paired approval separately covers Celery
bootstrap and immediate role-switch Principal refresh; see its preserved record.
No new dependency or test-harness relaxation was introduced.

## 3.7 — Scheduled work and operations

`tasks.release_content` runs an ID-only ETA job after a committed schedule change.
`tasks.release_due_materials` and `tasks.release_due_assignments` are 60-second
Celery beat catch-up sweeps, each limited to 50 ordered due IDs. Both paths call
`releases.transition_content`, re-read state/time under lock, and append an audit
only for a successful transition. Validation failure is logged and leaves content
private; dispatch failure is logged and the catch-up sweep recovers due rows.
Duplicate workers, stale ETAs and withdrawn items cannot republish or duplicate
audit. GET never changes lifecycle state. Broker/worker availability determines
observed dispatch latency; a timestamp does not promise delivery while workers stop.

| Operator command | Purpose |
|---|---|
| `manage.py sync_lms_workspaces` | Idempotent paginated IAM scaffold/default-policy refresh; preserves Faculty content. |
| `manage.py check_lms_ready` | Actionable prerequisite check for IAM/settings, workspace sync and private storage. |
| `manage.py release_due_materials` | Manual bounded material catch-up through the same transition path. |
| `manage.py release_due_assignments` | Manual bounded assignment catch-up through the same transition path. |

Deployment: configure IAM/DB/private storage and Redis; migrate; synchronize
workspaces; seed modules and the generated IAM permission manifest; check readiness;
start API, client, Celery worker and beat. Production uses non-eager tasks. The
supplied dev settings force eager mode, so local real-worker checks use an external
settings overlay overriding only `CELERY_TASK_ALWAYS_EAGER=False`, never a committed
test-settings or harness change. D-01/D-03/D-05 add no separate scheduler job.

## 3.8 — Approval and review status

| Milestone | Actual status |
|---|---|
| BPR-001 | IAM implementation committed/verified locally at the pinned revision; no upstream merge claimed. |
| BPR-002 | Actual local lms_ta/lms_observer designations and mandatory permission/module/offering gates implemented; pair-endorsed identifiers. |
| BPR-003 | D-01–D-06 adopted and retained in policy record. |
| BPR-004 | Human paired approval of exact A9-LMS-BP-0.2 documentation commit received 22 November 2026. |
| BPR-005 / F-03 | Approved shared private writer implemented and tested. |
| F-04 / Q-04 | Approved mutability rules implemented with assignment-first locking and regressions. |
| F-05 / Q-05 | ETA plus bounded beat fallback implemented and exercised with real workers. |
| Shared corrections | Paired dated approval of exact config bootstrap and auth refresh received 23 November; preserved unedited. |
| Step 7 | Completed Round 2 found 17 issues on 92b4ed5; corrections and builder checks are recorded separately. No subsequent independent 10/10 verdict is claimed. |
| Step 8 | Not started. Student 1 has not created/touched either reserved spec-test directory. |

The PR remains a draft while the final independent review and Student 2 phase are
outstanding. Historical approvals and unedited review output remain preserved;
builder verification is not an independent scorecard.
