# 10-lms/OPEN_ISSUES.md — LMS Course Management Open Issues Register

Overview:
Explicitly document the 6 unresolved policy questions identified in Problem Statement v1.0 §5 and synchronized specification documents. Per mandatory instructions, NO policy is invented. All 6 remain in status 'NEEDS CLARIFICATION'.

For each issue, detail:
- Issue ID
- Specification Source
- Unresolved Question
- Status (NEEDS CLARIFICATION)
- Safe Baseline Implementation Constraint

List of issues:

1. **ISS-LMS-001: Late-Submission Policy**
   - **Source:** Problem Statement §5, BR-LMS-013, UC-LMS-010.
   - **Question:** Is late submission hard-blocked, flagged as late, or overridable by faculty/admin?
   - **Status:** NEEDS CLARIFICATION
   - **Baseline Constraint:** Strict deadline enforcement (t <= t_due). After due date, submission is rejected with an informative error until policy is clarified.

2. **ISS-LMS-002: TA Permissions (Announcements & Grading)**
   - **Source:** Problem Statement §5, BR-LMS-007, BR-LMS-015, AFR-LMS-014.2, AFR-LMS-014.4.
   - **Question:** Are TA permissions to post announcements and grade submissions configurable per course or globally fixed?
   - **Status:** NEEDS CLARIFICATION
   - **Baseline Constraint:** Course-level configuration flags (allow_ta_announcements default False, allow_ta_grading default True) with TA attribution always recorded.

3. **ISS-LMS-003: Notification Delivery Channels**
   - **Source:** Problem Statement §5, CFR-LMS-006, UC-LMS-005, UC-LMS-013.
   - **Question:** Are notifications delivered via in-app alerts, email, or both?
   - **Status:** NEEDS CLARIFICATION
   - **Baseline Constraint:** Internal notification event logging and transactional outbox records. No hardcoded external SMTP dependency.

4. **ISS-LMS-004: Observer Linkage Granularity**
   - **Source:** Problem Statement §5, BR-LMS-003, AFR-LMS-015.1.
   - **Question:** Is an Observer linked to one specific student or to an entire course section?
   - **Status:** NEEDS CLARIFICATION
   - **Baseline Constraint:** Linkage is at the course/section level with strict prohibition of student-specific data access (grades, submissions).

5. **ISS-LMS-005: Resubmission Policy**
   - **Source:** Problem Statement §5, UC-LMS-010, AFR-LMS-011.1.
   - **Question:** How many submission attempts are permitted? How are late resubmissions handled?
   - **Status:** NEEDS CLARIFICATION
   - **Baseline Constraint:** Versioned submission history with single active submission attempt before due date until multi-attempt policy is authorized.

6. **ISS-LMS-006: Post-Release Grade Change Authority & Effects**
   - **Source:** Problem Statement §5, BR-LMS-019, UC-LMS-012, AFR-LMS-013.6.
   - **Question:** Who is authorized to alter grades after release, and what downstream recalculation effects are permitted?
   - **Status:** NEEDS CLARIFICATION
   - **Baseline Constraint:** Faculty-only edits with mandatory immutable GradeAuditLog recording assessor, timestamp, previous score, new score, and reason.