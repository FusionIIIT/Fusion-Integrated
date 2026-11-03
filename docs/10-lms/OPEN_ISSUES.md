# 10-lms/OPEN_ISSUES.md — LMS Course Management Open Issues Register

## Overview
Explicitly document the six unresolved policy questions identified in the Problem Statement (v1.0 §5) and synchronized specification documents. **No policy is invented**; all six remain in status **NEEDS CLARIFICATION**.

### Issue format
- **Issue ID**
- **Specification Source**
- **Unresolved Question** (what is unknown)
- **Known Specification** (what the spec confirms)
- **Status** – always `NEEDS CLARIFICATION`

## Open Issues

1. **ISS‑LMS‑001: Late‑Submission Policy**
   - **Source:** Problem Statement §5, BR‑LMS‑013, UC‑LMS‑010.
   - **Unresolved Question:** Whether a late submission is hard‑blocked, merely flagged as late, or overridable by faculty/administrators.
   - **Known Specification:** Submissions have a `status` field that can represent `late`.
   - **Status:** `NEEDS CLARIFICATION`

2. **ISS‑LMS‑002: TA Permissions (Announcements & Grading)**
   - **Source:** Problem Statement §5, BR‑LMS‑007, BR‑LMS‑015, AFR‑LMS‑014.2, AFR‑LMS‑014.4.
   - **Unresolved Question:** Whether TA permissions to post announcements and grade submissions are configurable per‑course or globally fixed.
   - **Known Specification:** Roles (`ta`) exist and can perform actions, but configurability is not defined.
   - **Status:** `NEEDS CLARIFICATION`

3. **ISS‑LMS‑003: Notification Delivery Channels**
   - **Source:** Problem Statement §5, CFR‑LMS‑006, UC‑LMS‑005, UC‑LMS‑013.
   - **Unresolved Question:** Which channels (in‑app alerts, email, both) are used for notifications.
   - **Known Specification:** A notification event log exists; external delivery mechanisms are unspecified.
   - **Status:** `NEEDS CLARIFICATION`

4. **ISS‑LMS‑004: Observer Linkage Granularity**
   - **Source:** Problem Statement §5, BR‑LMS‑003, AFR‑LMS‑015.1.
   - **Unresolved Question:** Whether an Observer links to a single student or to an entire course/section.
   - **Known Specification:** Observers are defined, but linkage scope is not detailed.
   - **Status:** `NEEDS CLARIFICATION`

5. **ISS‑LMS‑005: Resubmission Policy**
   - **Source:** Problem Statement §5, UC‑LMS‑010, AFR‑LMS‑011.1.
   - **Unresolved Question:** Number of allowed submission attempts and handling of late resubmissions.
   - **Known Specification:** `Submission.version` exists; semantics are not specified.
   - **Status:** `NEEDS CLARIFICATION`

6. **ISS‑LMS‑006: Post‑Release Grade Change Authority & Effects**
   - **Source:** Problem Statement §5, BR‑LMS‑019, UC‑LMS‑012, AFR‑LMS‑013.6.
   - **Unresolved Question:** Who may alter grades after release and what downstream recalculations are permitted.
   - **Known Specification:** `GradeAuditLog` is required; authority is not defined.
   - **Status:** `NEEDS CLARIFICATION`

*ISS‑LMS‑006 is a derived clarification rather than a direct Problem‑Statement question; it is kept here for traceability.*
