# Quiz Management Quality Report

**Module:** Quiz Management (`quiz`)
**Documentation number:** `20`
**Primary Developer:** Student 1
**Status:** Implementation and verification completed; Student 2 issued final independent acceptance **PASS** on 2026-11-21 with a score of **90/90 (100%)**. See [the final acceptance review](final-acceptance-review.md) for the complete scorecard and evidence.

This report preserves the Phase 2 approval record and known-gap register, and adds final implementation and verification results. Student 2's peer acceptance does not mark instructor or institutional questions as approved or resolved. Remaining integration and policy boundaries are listed below.

## 10. Known gaps accepted

Student 2 approved the documented known gaps and provisional boundaries subject to the conditions in §11. “Accepted” below means accepted as a documented gap for the approved blueprint; it does not resolve the underlying policy, integration or institutional decision. Decision and source IDs are retained from [the blueprint](quiz-blueprint.md).

| Gap / decision | Source or specification IDs | Known gap and reason it remains open | Disposition |
|---|---|---|---|
| UAD-01 | UC-QZ-018; BR-QZ-006, BR-QZ-017; BW-QZ-03, BW-QZ-05 | Confirm whether active attempts may finish after quiz closure. Peer-provisional behavior allows completion of allocated duration; instructor confirmation is pending. | Accepted as documented; underlying decision pending. |
| UAD-02 | AFR-QZ-006.4, AFR-QZ-011.1–.3; BR-QZ-018, BR-QZ-020; ISS-QZ-002 | MSQ all-or-nothing is peer-provisional; approved scoring policy and any relationship to negative marking still require authority. | Accepted as documented; instructor decision pending. |
| UAD-03 | AFR-QZ-006.5, AFR-QZ-013.2–.3, AFR-QZ-014.1–.3; BR-QZ-021; ISS-QZ-003 | Exact visibility of marks, feedback, answers and history after release is unsettled. | Accepted as documented; instructor decision pending. |
| UAD-04 | AFR-QZ-004.3, AFR-QZ-006.4, AFR-QZ-011.2; BR-QZ-011 | Precedence between question-level and quiz-level negative marking is unspecified. | Accepted as documented; instructor decision pending. |
| UAD-05 | AFR-QZ-008.4; BR-QZ-013, BR-QZ-014; UC-QZ-008; ISS-QZ-004, ISS-QZ-005 | Browser focus/visibility behavior and the acceptable interpretation of OS application inspection require clarification. | Accepted as documented; instructor decision pending. |
| AF-05 | AFR-QZ-002.4, AFR-QZ-008.2, AFR-QZ-013.1, AFR-QZ-014.2–.3, AFR-QZ-015.2 | A single aggregate score across attempts and metric denominators are not specified. | Accepted as documented; policy decision pending. |
| AF-07 | AFR-QZ-012.2–.5; UC-QZ-013; BR-QZ-019; ISS-QZ-008 | No external AI provider or approved student-data handling contract is established. | Accepted as documented; provider and privacy decisions pending. |
| DEC-QZ-SAMPLE | AFR-QZ-006.2; BR-QZ-009; ISS-QZ-002 | Sampling is required, but whether selection occurs at publication or per attempt is unspecified. | Accepted as documented; policy decision pending. |
| DEC-QZ-BANK | AFR-QZ-004.4–.5, AFR-QZ-005.1–.3; BR-QZ-005 | Versioned bank references versus quiz snapshots are unresolved. | Accepted as documented; design decision pending. |
| DEC-QZ-FILE | AFR-QZ-004.5 | Private image upload/storage handling depends on confirming whether `core.files` meets the requirements. | Accepted as documented; storage contract pending. |
| DEC-QZ-RETENTION | AFR-QZ-003.4; BR-QZ-023; ISS-QZ-001 | Retention and purge rules for quizzes, attempts, results, audit records and attachments are unspecified. | Accepted as documented; policy decision pending. |
| DEC-QZ-GRACE | BR-QZ-017; UC-QZ-011; BW-QZ-05 | A 15-second grace period is not in the synchronized requirements and conflicts with the stated expiry boundary. | Accepted as documented; no grace behavior authorized by this record. |
| DEC-QZ-HARD-DELETE | AFR-QZ-003.4; BR-QZ-023 | The source phrase “where permitted” does not establish deletion authority or retention behavior. | Accepted as documented; policy decision pending. |
| DEC-QZ-NOTIFY | AFR-QZ-016.1–.2; BR-QZ-024; UC-QZ-019; ISS-QZ-008 | Notification transport, audience fanout and delivery guarantees have no approved external contract. | Accepted as documented; transport remains unresolved. |
| Scheduled-edit boundary | BR-QZ-005; UC-QZ-001, UC-QZ-002, UC-QZ-004, UC-QZ-005; BW-QZ-01, BW-QZ-02 | Locking edits at `Scheduled` is peer-provisional and tightens the source phrase “before active.” | Accepted as documented; instructor confirmation pending. |
| Actor/designation mapping | CFR-QZ-001; AFR-QZ-001.1–.4 | The exact Professor ERP designation and associated course authorization cannot be verified from the current checkout. | Accepted as documented; IAM mapping pending. |
| OS application inspection | AFR-QZ-008.4; BR-QZ-014; UC-QZ-008; ISS-QZ-005 | A browser cannot be assumed to inspect or close arbitrary OS applications; acceptable source interpretation remains open. | Accepted as documented; requirement clarification pending. |

The twelve peer-accepted provisional decisions remain identified in the blueprint. This approval accepts the boundaries as documented; it does not convert them into instructor or institutional policy.

## 11. Approval record

### Formal Phase 2 blueprint approval

- **Reviewer:** Student 2 — Independent Reviewer & QA Lead
- **Primary Developer:** Student 1
- **Approved baseline:** `docs/20-quiz/quiz-blueprint.md`
- **Verdict:** **APPROVED WITH CONDITIONS**
- **Date:** 2026-11-20
- **Timestamp:** `2026-11-20T23:45:06+05:30`
- **Authorization (exact supplied wording):** “Student 2 grants written Phase 2 blueprint approval. Student 1 may proceed to Phase 3.”
- **Approval scope:** Student 2 approved the documented known gaps and provisional boundaries, subject to the conditions below.
- **Record source:** Dated written approval details supplied by Student 2. No approval URL or separate repository attachment was supplied; none is invented here.

### Conditions

1. Use Phosphor icon identifiers without the `Fa` prefix.
2. Follow backend layer dependency order: domain, models/migrations, selectors, services, tasks, API serializers/views.
3. External identities must remain integer scalar `user_id` references; no cross-module foreign keys.
4. Runtime verification, migrations and tests must wait until Docker Compose, PostgreSQL, Redis and Celery prerequisites are verified as running.

This is Student 2’s peer approval under the assignment. It is not instructor, institutional, IAM, privacy, academic or security approval. The pending decisions listed in §10 and the blueprint’s Step 3.8 remain open until their named authority decides them. The earlier date of the written agreement on the twelve peer decisions was not supplied and is not inferred.

### Historical Phase 2 environment snapshot

The following blockers were recorded during the Phase 2 read-only environment inspection. They describe that earlier inspection, not the later Ubuntu WSL test environment:

- The expected sibling `Fusion_System_Administrator` checkout and a `fusion-dev.dump` fixture were not found in the inspected locations. The separate IAM checkout and fixture acquisition were therefore not verified at that time.
- Docker was unavailable in that inspected Windows environment; the checked PostgreSQL and Redis ports had no listeners, and Celery worker/broker readiness was not verified.
- The checked IAM, platform, and client service ports had no listeners. `client/node_modules` and separate `Fusion` / `Fusion-client` checkouts were absent. The separate Fusion-client integration target was not verified.
- The module-only guide's documented setup path was to obtain the IAM checkout and database fixture, restore the fixture as `fusionlab`, configure and migrate IAM and run `sync_identity`, then start Docker Compose services, IAM, the platform (`make dev`) and client (`cd client && npm install && npm run dev`) before verifying fixture login and Placement visibility. This historical checklist does not assert that full IAM or client end-to-end setup was later completed.

### Final independent acceptance record

- **Reviewer:** Student 2 — Independent Reviewer & QA Lead
- **Candidate:** Student 1 — Implementation Lead
- **Assignment:** Assignment 9 — Quiz Management
- **Review date:** November 21, 2026 (reissued and reconfirmed)
- **Verdict:** **PASS**
- **Composite score:** **90/90 (100%)**; all nine dimensions scored 10/10.
- **Authorization:** “Student 1 is FULLY AUTHORIZED for final submission of Assignment 9.”
- **Record:** [Final independent acceptance review](final-acceptance-review.md). This is Student 2's peer review, not instructor or institutional approval.

## Implementation and verification completed

The final acceptance review records completion of the Quiz domain, Django models and initial migration, selectors, services, Celery tasks and schedules, and API views and serializers. The module is registered with Django, mounted under `/api/v1/quiz/`, and its task routes and beat schedule are merged with Placement's configuration. External user and course identities remain scalar IDs; unavailable academic authorization boundaries fail closed. The review records no cross-module foreign keys.

The final acceptance review records the following results. The two pytest suite totals were freshly reproduced in Ubuntu WSL against the current working tree during the final verification:

| Check | Result |
|---|---|
| `modules/quiz/tests/` | **76 passed**; no failures, errors or skips. |
| `modules/placement/tests/test_schedule.py` | **8 passed**; no failures, errors or skips. |
| `python manage.py check` | Passed; no system check issues. |
| `python manage.py makemigrations --check --dry-run` | Passed; no changes detected. |
| Ruff checks | `ruff check` passed; `ruff format --check` passed for the reviewed 41 files, as recorded by Student 2. |

The fresh pytest runs completed in Ubuntu WSL using `.venv-wsl/bin/python`, PostgreSQL database `fusionlab`, and the configured Redis broker. A repository search found no retained historical pytest or JUnit logs; the cited test totals are supported by the reissued review and fresh execution, not by an archived test log.

## Remaining platform prerequisites and unresolved decisions

The PASS verdict is peer acceptance of the implementation and documented boundaries. It does not implement, approve, or resolve these outstanding items:

- **Academic authorization and roster eligibility:** Production course scope and student enrollment eligibility providers are not integrated. Protected API paths fail closed with HTTP 503; do not substitute client-supplied scope, fixtures, or synthetic authorization.
- **IAM role/designation mapping:** The authoritative Professor designation and course authorization mapping remain an IAM/platform-owner decision.
- **Question Bank policy:** Shared-bank authorization, mutation policy, versioning versus snapshots, and associated ownership rules remain unresolved. Current API behavior is read-only and creator-scoped.
- **Notification transport:** Internal outbox events may be recorded, but no external notification provider, recipient fanout, delivery guarantee, or transport is implemented or approved.
- **AI evaluation and privacy:** No live external AI provider is integrated. Provider, privacy, data retention, and institutional approvals remain outstanding; manual Professor grading remains the provisional boundary.
- **File storage:** Private image/file upload and storage contract remain unresolved pending confirmation of the platform file service.
- **Assessment policy:** The accepted peer decisions remain provisional. Instructor decisions remain open for close/deadline behavior, score visibility and history, negative-marking precedence, random-sampling timing, retention and deletion, scheduled-edit locking, aggregate-score semantics, OS application inspection, and other items in the known-gap register above and blueprint §3.8.
- **Scheduled boundary policy:** The final review records that a scheduled quiz which passes `close_at` before activation is left unchanged by the boundary task; institutional policy for that case remains open.
- **API schema documentation:** The final review records drf-spectacular fallback notices for custom APIViews; full schema annotations remain identified as later hardening work.

Earlier environment checks in the Phase 2 record are retained as historical findings and setup guidance, not as the current runtime status. The final review records successful database-backed tests and migration checks from Ubuntu WSL. Separate IAM/academic integration and institutional policy questions above remain open regardless of local test-environment availability.
