# LMS policy decisions — adopted ruling record

**Decision version:** A9-LMS-D-2026-11-22-v2

**Received:** 22 November 2026 (IST)

**Authority represented:** Formal Student 2 ruling supplied through Student 1

**Blueprint approval:** Continues to be withheld

This record separates adopted clarifications from the unchanged LMS v1.0 source documents. The original forwarded ruling is preserved in the external run/review record. Its identity and exact hash are recorded in the blueprint manifest; this document does not reproduce personal identifiers or claim a completed blueprint approval.

## D-01 — Submission deadline

The time condition is satisfied when the authoritative server UTC `submission_timestamp <= assignment.due_date`; equality is accepted. Use `django.utils.timezone.now()` for the persisted timestamp and deadline decision. This is an adopted boundary clarification to the source's general “before the due date” wording.

After the due time, refuse with `422` and `SUBMISSION_DUE_DATE_EXCEEDED`. Source registration, visibility, assignment availability, payload validity and D-05 uniqueness checks remain required; meeting the time condition alone is not sufficient for acceptance.

Late flagging, grace periods and instructor overrides are approved scope deferrals for this baseline. The module does not create a late submission through the normal submission API. Submission history retains the original status vocabulary where applicable without inventing late acceptance.

**Source relationship:** PS §§3.5/5, BR-LMS-013, AFR-LMS-008.2; explicit pair-level clarification of previously open policy.

## D-02 — TA capabilities and announcements

An authoritatively course-assigned TA may grade that course's submissions. Every grading action is attributed to the actual actor. Faculty alone releases grades; TA release attempts receive `403`.

`can_ta_post_announcements` is a course-level boolean, false by default. When true, any assigned TA for that course may post announcements. When false, TA posting receives `403`. Faculty changes it through an effective-dated policy version in the planned platform-compatible design; old policy versions are not edited.

TA authority does not include assignment/material/course-structure creation or editing. The basic Student role is not used to give every Student TA powers; real acting-role mapping and source associations remain dependencies.

**Source relationship:** PS §2.3; BR-LMS-004/007/015/017. Configuration mechanism/default and course-wide application are adopted clarifications.

## D-03 — Visibility instead of outbound notifications

The baseline is satisfied by pull-based visibility in course announcement and released-grade views. No separate notification feed, unread counter or notification bell is required by this ruling.

Email, push and SMS delivery are explicitly deferred pending a supported unified notification contract. This is the adopted scope decision; it is not represented as an email prohibition already present in PS §4.

**Source relationship:** PS §3.3 and notification open question; BR-LMS-008's unresolved channel exception.

## D-04 — Observer linkage and privacy

Observers are linked at course-offering/section level through the authoritative upstream association source. They may read syllabus, course instructor/TA contacts, published materials and announcements. They may not read Student submissions, grades, class rosters or other Student-specific data, and may perform no writes.

Missing verb/role authority receives `403`. Nonexistent or outside-scope resources receive `404` under the platform's scoping convention. The ruling does not supply an existing IAM designation or course-linkage API; those remain unresolved prerequisites.

**Source relationship:** PS §§2.4/3.1, BR-LMS-001/003; approved granularity clarification.

## D-05 — One successfully recorded submission

Each Student may have at most one recorded submission per assignment. An attempt is consumed only by successfully recording the valid submission, returning `201`. Use D-01's exact inclusive deadline boundary.

Malformed requests (`400`), invalid submission types (`422`), late submissions (`422`) and other rejected requests consume no attempt. A second submission after one has been recorded receives `409` with `SUBMISSION_ALREADY_EXISTS`. Enforce uniqueness in the database as well as in services; no mutable attempt counter or replacement/resubmission path is introduced.

**Source relationship:** PS §§3.5/5, BR-LMS-013 and Workflow §2; adopted single-attempt policy, not an original explicit attempt limit.

## D-06 — Released-grade corrections

Only assigned Faculty may change score/feedback after release. TAs receive `403` for that operation. A successful correction retains `RELEASED`, preserving Student visibility.

The same transaction writes an immutable `GradeAuditLog` with `submission_id`, Faculty `actor_id`, previous/new score, previous/new feedback and UTC `changed_at`. If the audit write fails, the grade change must roll back. Students and Observers receive no grade-write authority.

**Source relationship:** PS §3.6, BR-LMS-019, UC-LMS-012. Actor/time audit is the original obligation; Faculty-only authority, retained Released state and explicit before/after fields are adopted clarifications/extensions. They must not be falsely attributed to unchanged BR-LMS-019 alone.

## Common API classification adopted in the ruling

All module endpoints use `/api/v1/lms/`. Apply the existing error envelope and these categories deliberately:

| Status | Category |
|---|---|
| 400 | Syntactically malformed payloads or omitted structurally required fields |
| 401 | Unauthenticated requests |
| 403 | Authenticated callers lacking the required action/role permission |
| 404 | Nonexistent resources or resources outside authorized course/ownership scope |
| 409 | Lifecycle/uniqueness conflicts, including an already recorded submission |
| 422 | Semantic or business-rule refusal, including deadline exceeded, type mismatch or negative points |

## Additional adopted Stage A design rulings

The staged authorization received on 22 November 2026, SHA-256 `2c887167c5a212a04f36245cc5b0da56f4d3edb50e6719421fe4553898ebf1a1`, adopts:

- **F-03:** Module-neutral private `core/files/writers.py`, standard-library content verification, 25,000,000-byte material / 10,000,000-byte submission caps, allowed `.pdf/.zip/.tar.gz/.txt/.docx/.ipynb`, blocked direct executable/scriptable formats, sanitized parent-authorized attachment streaming. Shared implementation remains Stage B work.
- **F-04:** Submission type immutable after first successful submission; points possible immutable after first grade; due date may remain or extend monotonically and never precede any recorded submission. Faculty may edit instructions/title. Invalid edits receive 422 with no state change.
- **F-05:** Post-commit ETA dispatch plus 60-second, 50-item catch-up scans. Lock and re-read current state/time to avoid early/duplicate transitions and audits.
- **Actor model:** Real local `lms_ta`/`lms_observer` markers plus module grant, action permission and live offering scope. Context roles never bypass `HasPermission` or union different acting roles.
- **Working identifiers:** `lms` and `docs/10-lms/` are pair working values. Separate official instructor confirmation is not claimed.

## Remaining authorization boundary

Stage A is delivered at local IAM revision `494160849bd101a5cb77a1b1c9f0881307079888` with 341 passing PostgreSQL tests and actual HTTP 200 verification of both course endpoints. Its source registrations remain unchanged; synthetic nonstudent data are labelled explicitly. Stage A authorization does not approve LMS application implementation. The actual approver must review the revised blueprint A9-LMS-BP-0.2 and prerequisite evidence and issue the separate dated final decision before Stage B code or builder tests begin.
