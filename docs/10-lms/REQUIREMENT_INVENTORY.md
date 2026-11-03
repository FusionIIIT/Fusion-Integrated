# 10-lms/REQUIREMENT_INVENTORY.md — Canonical Specification Inventory

## 1. Inventory Summary
- **Core Functional Requirements (CFR-LMS):** 15 Core Functional Requirements (CFR-LMS-001 through CFR-LMS-015)
- **Atomic Functional Requirements (AFR-LMS):** 47 Atomic Functional Requirements (AFR-LMS-001.1 through AFR-LMS-015.4)
- **Business Rules (BR-LMS):** 19 Business Rules (BR-LMS-001 through BR-LMS-019)
- **Use Cases (UC-LMS):** 15 Use Cases (UC-LMS-001 through UC-LMS-015)
- **Basis Workflows (BW-LMS):** 5 Basis Workflows (BW-LMS-01 through BW-LMS-05)
- **Composite Workflows (CW-LMS):** 2 Composite Workflows (CW-LMS-01 and CW-LMS-02)
- **Open Issues (ISS-LMS):** 6 Open Issues (ISS-LMS-001 through ISS-LMS-006)

## 2. Complete CFR Table with Mapped AFRs and Descriptions

| CFR ID | Description | Mapped AFRs |
|--------|-------------|------------|
| **CFR-LMS-001** | Access course workspace and view course home | AFR-LMS-001.1, 001.2, 001.3 |
| **CFR-LMS-002** | Manage course workspace details | AFR-LMS-002.1, 002.2 |
| **CFR-LMS-003** | Upload and organize course materials | AFR-LMS-003.1, 003.2, 003.3, 003.4 |
| **CFR-LMS-004** | Schedule future release of course materials | AFR-LMS-004.1, 004.2 |
| **CFR-LMS-005** | View published course materials | AFR-LMS-005.1, 005.2 |
| **CFR-LMS-006** | Post timestamped course announcements | AFR-LMS-006.1, 006.2, 006.3, 006.4 |
| **CFR-LMS-007** | View course announcements | AFR-LMS-007.1, 007.2 |
| **CFR-LMS-008** | Create and edit assignments | AFR-LMS-008.1, 008.2, 008.3, 008.4 |
| **CFR-LMS-009** | Control assignment publication and release | AFR-LMS-009.1, 009.2, 009.3 |
| **CFR-LMS-010** | View and download published assignments | AFR-LMS-010.1, 010.2 |
| **CFR-LMS-011** | Submit assignment work | AFR-LMS-011.1, 011.2, 011.3 |
| **CFR-LMS-012** | Track student submission status and history | AFR-LMS-012.1, 012.2, 012.3 |
| **CFR-LMS-013** | Grade submissions and release results | AFR-LMS-013.1, 013.2, 013.3, 013.4, 013.5, 013.6 |
| **CFR-LMS-014** | Enforce Teaching Assistant capabilities and restrictions | AFR-LMS-014.1, 014.2, 014.3, 014.4, 014.5 |
| **CFR-LMS-015** | Enforce Observer read-only access and privacy | AFR-LMS-015.1, 015.2, 015.3, 015.4 |

## 3. Active Business Rules Table (BR-LMS-001 through BR-LMS-019)

| BR ID | Description |
|-------|-------------|
| **BR-LMS-001** | Course materials must be uploaded before they can be accessed by students. |
| **BR-LMS-002** | Only authorized users can modify course announcements. |
| **BR-LMS-003** | Students cannot submit assignments after the submission deadline has passed. |
| **BR-LMS-004** | Assignments must be graded within a specified timeframe to ensure timely feedback. |
| **BR-LMS-005** | Teaching Assistants have limited access and can only perform specific tasks related to grading and assignment management. |
| **BR-LMS-006** | Observers have read-only access and cannot make any changes to the course content or student submissions. |
| **BR-LMS-007** | Course materials must be organized in a logical manner for easy navigation by students. |
| **BR-LMS-008** | Announcements should include timestamps to indicate when they were posted. |
| **BR-LMS-009** | Assignments must have clear instructions and due dates specified. |
| **BR-LMS-010** | Students can only view their own submission history, not that of other students. |
| **BR-LMS-011** | Grading should be consistent across all assignments to maintain fairness. |
| **BR-LMS-012** | Course administrators must approve any changes made by Teaching Assistants before they take effect. |
| **BR-LMS-013** | Observers can only view course content and student submissions, but cannot interact with them in any way. |
| **BR-LMS-014** | All user actions within the LMS must be logged for auditing purposes. |
| **BR-LMS-015** | Course materials should be accessible from multiple devices and platforms. |
| **BR-LMS-016** | Students can only submit assignments through the designated submission portal. |
| **BR-LMS-017** | Course administrators must have the ability to override any user access restrictions if necessary. |
| **BR-LMS-018** | The LMS should provide notifications to students about upcoming deadlines and important announcements. |
| **BR-LMS-019** | All course materials must be compatible with standard file formats for easy integration. |

## 4. Active Use Cases Table (UC-LMS-001 through UC-LMS-015)

| UC ID | Description |
|-------|-------------|
| **UC-LMS-001** | As a student, I want to access the course workspace so that I can view and interact with course materials. |
| **UC-LMS-002** | As an instructor, I want to manage course details such as name and description so that I can provide clear information about the course. |
| **UC-LMS-003** | As a student, I want to upload and organize my own course materials so that they are easily accessible for review. |
| **UC-LMS-004** | As an instructor, I want to schedule future releases of course materials so that students can access them at the appropriate time. |
| **UC-LMS-005** | As a student, I want to view published course materials so that I can review and study them. |
| **UC-LMS-006** | As an instructor, I want to post timestamped announcements so that students are aware of important updates. |
| **UC-LMS-007** | As a student, I want to view course announcements so that I am informed about any changes or important information. |
| **UC-LMS-008** | As an instructor, I want to create and edit assignments so that I can set up tasks for students to complete. |
| **UC-LMS-009** | As an instructor, I want to control the publication and release of assignments so that they are available at the correct time. |
| **UC-LMS-010** | As a student, I want to view and download published assignments so that I can access them for review or submission. |
| **UC-LMS-011** | As a student, I want to submit assignment work so that my efforts are recorded and graded. |
| **UC-LMS-012** | As an instructor, I want to track the status of student submissions so that I can monitor their progress. |
| **UC-LMS-013** | As an instructor, I want to grade submitted assignments and release results so that students receive feedback on their work. |
| **UC-LMS-014** | As a Teaching Assistant, I want to enforce my capabilities and restrictions so that I can assist with grading without overstepping my role. |
| **UC-LMS-015** | As an Observer, I want to have read-only access to the course content and student submissions so that I can monitor progress without making changes. |

## 5. Workflows Table (BW-LMS-01 to 05)

| Workflow ID | Description |
|-------------|-------------|
| **BW-LMS-01** | Course Setup Workflow: Instructors set up the course by defining its name, description, and materials. |
| **BW-LMS-02** | Assignment Management Workflow: Instructors create, edit, and release assignments to students. |
| **BW-LMS-03** | Student Submission Workflow: Students submit their work for grading through the designated portal. |
| **BW-LMS-04** | Grading and Feedback Workflow: Instructors grade student submissions and provide feedback within the specified timeframe. |
| **BW-LMS-05** | Course Review Workflow: Instructors review course materials, announcements, and assignments to ensure they meet quality standards. |

## 6. Composite Workflows Table (CW-LMS-01 and CW-LMS-02)

| Workflow ID | Description |
|-------------|-------------|
| **CW-LMS-01** | Course Launch Workflow: Instructors prepare the course for launch by setting up materials, announcements, and assignments. |
| **CW-LMS-02** | Student Completion Workflow: Students follow a structured process to complete their coursework, from submission to receiving feedback. |

## 7. Open Issues Table (ISS-LMS-001 through ISS-LMS-006)

| Issue ID | Title / Scope | Status | Specification Question |
| :--- | :--- | :--- | :--- |
| **ISS-LMS-001** | Late-Submission Policy (Hard-blocked vs flagged late vs overridable) | NEEDS CLARIFICATION | Should the system hard-block submissions after a certain time, flag them as late but allow overrides, or allow all submissions until the due date? |
| **ISS-LMS-002** | TA Permissions for Announcements & Grading (Configurable vs fixed) | NEEDS CLARIFICATION | Should Teaching Assistants have configurable permissions to manage announcements and grading, or should these permissions be fixed based on their role? |
| **ISS-LMS-003** | Notification Delivery Channels (In-app alerts vs email vs outbox) | NEEDS CLARIFICATION | How should notifications be delivered—through in-app alerts, emails, or a combination of both—and what are the implications for each method? |
| **ISS-LMS-004** | Observer Linkage Granularity (Course-level vs individual student) | NEEDS CLARIFICATION | Should observers have access to course-level data only, or should they be able to view detailed information about individual students within a course? |
| **ISS-LMS-005** | Resubmission Policy (Multi-attempt vs single-attempt before due date) | NEEDS CLARIFICATION | Should the system allow multiple attempts for assignments before the due date, or should only one attempt be allowed until the submission deadline? |
| **ISS-LMS-006** | Post-Release Grade Change Authority & Audit Effects (Faculty-only vs TA override) | NEEDS CLARIFICATION | Who should have the authority to change grades after they have been released—only faculty members, or should Teaching Assistants also be allowed to make such changes with audit trails? |
