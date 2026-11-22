# Quiz Management Module Blueprint (`docs/20-quiz/quiz-blueprint.md`)

## Module Metadata
- **Module Name:** Quiz Management (Quizzes)
- **Module Code:** `quiz`
- **Docs Folder:** `docs/20-quiz/`
- **Spec Folder:** `20-QUIZZES`
- **Spec ID Prefixes:** `BR-QZ-`, `UC-QZ-`, `AFR-QZ-`, `CFR-QZ-`, `BW-QZ-`, `CW-QZ-`
- **Environment:** `module-only`

---

## 3.1 (a) Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-QZ-001 | Role separation: Students cannot manage quizzes; Professors manage | API & IAM | `registry.py` & `api/permissions.py` | Enforced at entry gates |
| BR-QZ-002 | Professor course scope: Professors manage quizzes only for their courses | Selectors & Services | `selectors/scoping.py` | Returns 404 on unpermitted rows |
| BR-QZ-003 | Student quiz eligibility: Students see only assigned/eligible quizzes | Selectors & Services | `selectors/scoping.py` | Scoped to student course enrollments |
| BR-QZ-004 | Student-specific data visibility: Attempt answers visible only to student & grading faculty | Selectors & API | `selectors/scoping.py` | 404 for unauthorized users |
| BR-QZ-005 | Pre-activation edit boundary: Quizzes/questions editable only in Draft/Configured states | Domain & Services | `domain/state_machine.py` | Locked once published/scheduled |
| BR-QZ-006 | Availability window: Attempts permitted strictly within `start_at` and `close_at` | Domain & Services | `domain/rules.py` & `services/attempt_service.py` | Rejects start outside window |
| BR-QZ-007 | Time limit: Attempt duration strictly enforced | Domain & Models | `models.py` & `services/attempt_service.py` | `deadline_at` set at attempt creation |
| BR-QZ-008 | Permitted attempts: Student cannot exceed `max_attempts` | Domain & Services | `domain/rules.py` & `models.py` | Constrained by attempt count validation |
| BR-QZ-009 | Question/option selection & order: Deterministic random shuffle via seed | Domain & Services | `domain/scoring.py` & `services/attempt_service.py` | Shuffled sequence saved in attempt |
| BR-QZ-010 | Navigation mode: Back navigation allowed or forbidden per quiz settings | Services & Client | `services/attempt_service.py` & frontend | Monitored and validated on answer save |
| BR-QZ-011 | Negative marking: Configurable penalty applied only on incorrect objective answers | Domain | `domain/scoring.py` | Pure calculation in domain layer |
| BR-QZ-012 | Unanswered-question rule: Enforce whether student may leave blanks on submission | Domain & Services | `domain/rules.py` & `services/attempt_service.py` | Validated at manual submission |
| BR-QZ-013 | Tab-block rule: Track tab-switch events; auto-submit if limit reached | Services | `services/attempt_service.py` | `tab_violations >= limit` triggers auto-submit |
| BR-QZ-014 | Background app check/environment: Client logs environment status | Client & Audit | `client/src/modules/quiz/` & `AuditLogEntry` | Client security monitor |
| BR-QZ-015 | Active response persistence: Save progress continuously | Services | `services/attempt_service.py::save_response` | Upsert to `AttemptResponse` |
| BR-QZ-016 | Submitted attempt immutability: Once submitted, answers cannot change | Domain & Models | `domain/state_machine.py` | Terminal attempt state |
| BR-QZ-017 | Time-expiry auto-submit: Background job submits expired attempts | Tasks & Services | `schedule.py` & `services/attempt_service.py` | Periodic beat runner |
| BR-QZ-018 | Objective evaluation: Instant calculation for MCQ, MSQ, TF, FIB | Domain | `domain/scoring.py` | Auto-calculates `auto_marks` |
| BR-QZ-019 | Professor authority over subjective/AI marks: Professor has final sign-off | Services | `services/evaluation_service.py` | `final_marks` set only by professor |
| BR-QZ-020 | Result calculation: Compute total marks, percentage, pass/fail | Domain | `domain/scoring.py` | Atomic result generation |
| BR-QZ-021 | Result release/visibility: Results invisible until Professor releases | Domain & Selectors | `domain/state_machine.py` & `selectors/scoping.py` | Guard prevents student view before `RELEASED` |
| BR-QZ-022 | Audit trail: Append-only event log for quiz lifecycle | Models & Services | `models.py::AuditLogEntry` | Write-only, immutable |
| BR-QZ-023 | Archive/delete permission: Quiz can be archived only from Closed state | Domain & Services | `domain/state_machine.py` | Refuses archive unless closed |
| BR-QZ-024 | Notification events: Publish events on key lifecycle milestones | Services & Models | `models.py::Notification` | Outbox notifications |
| UC-QZ-001 | Create / Edit Quiz | Services & API | `services/quiz_service.py` & `api/views.py` | Professor creates quiz in Draft |
| UC-QZ-002 | Manage Quiz Questions | Services & API | `services/question_service.py` | Add/update/reorder questions in draft |
| UC-QZ-003 | Manage Question Bank | Services & API | `services/question_service.py` | Search, filter, store bank items |
| UC-QZ-004 | Configure Quiz and Schedule | Services & API | `services/quiz_service.py` | Settings & schedule timing |
| UC-QZ-005 | Publish / Schedule Quiz | Services & API | `services/quiz_service.py` | Moves quiz to Scheduled or Available |
| UC-QZ-006 | Archive / Delete Quiz | Services & API | `services/quiz_service.py` | Transition to Archived or soft-delete |
| UC-QZ-007 | View Eligible Quizzes & Instructions | Selectors & API | `selectors/quizzes.py` | Student dashboard of quizzes |
| UC-QZ-008 | Start Quiz Attempt | Services & API | `services/attempt_service.py` | Initializes attempt, seed, timer |
| UC-QZ-009 | Attempt Quiz and Save Responses | Services & API | `services/attempt_service.py` | Periodic answer saving |
| UC-QZ-010 | Submit Quiz Attempt | Services & API | `services/attempt_service.py` | Student manual submission |
| UC-QZ-011 | Auto-Submit Expired Attempt | Tasks & Services | `tasks.py` & `services/attempt_service.py` | Triggered by beat or deadline check |
| UC-QZ-012 | Automatically Evaluate Objective Responses | Domain & Services | `services/evaluation_service.py` | Triggered upon submission |
| UC-QZ-013 | Evaluate Subjective Responses | Services & API | `services/evaluation_service.py` | Professor scores short/long answers |
| UC-QZ-014 | Release Quiz Results | Services & API | `services/evaluation_service.py` | Releases result to students |
| UC-QZ-015 | View Released Quiz Result | Selectors & API | `selectors/evaluations.py` | Student views score & breakdown |
| UC-QZ-016 | View Quiz Submissions & Performance Reports | Selectors & API | `selectors/evaluations.py` | Professor analytics dashboard |
| UC-QZ-017 | View Student Quiz Performance History | Selectors & API | `selectors/evaluations.py` | Student historical scores |
| UC-QZ-018 | Process Quiz Availability Boundary | Tasks & Services | `tasks.py` & `services/quiz_service.py` | Scheduled to Available / Available to Closed |
| UC-QZ-019 | Generate Quiz Event Notification | Services & Models | `models.py::Notification` | Notification dispatcher |

---

## 3.2 (b) Domain Model

Entities, fields, invariants, and database constraints:
1. **Quiz** (`quiz_quiz`):
   - Fields: `id`, `course_id`, `title`, `instructions`, `status` (DRAFT, DRAFT_CONFIGURED, READY_TO_PUBLISH, SCHEDULED, AVAILABLE, CLOSED, ARCHIVED), `created_by_user_id`, `start_at`, `close_at`, `duration_minutes`, `max_attempts`, `created_at`, `updated_at`.
   - Constraints:
     - `CheckConstraint(duration_minutes > 0)`
     - `CheckConstraint(max_attempts > 0)`
     - `CheckConstraint(close_at IS NULL OR start_at IS NULL OR close_at > start_at)`
2. **QuizSettings** (`quiz_settings`):
   - Fields: `quiz_id`, `allow_unanswered`, `back_navigation`, `tab_violation_limit`, `negative_marking_enabled`, `result_visibility` (FULL, MARKS_ONLY, HIDDEN).
3. **QuestionBankItem** (`quiz_question_bank`):
   - Fields: `id`, `owner_user_id`, `question_text`, `question_type` (MCQ, MSQ, TF, FIB, SHORT, LONG), `topic`, `difficulty`, `marks`, `negative_marks`, `image`, `created_at`, `updated_at`.
4. **QuizQuestion** (`quiz_question`):
   - Fields: `quiz_id`, `question_text`, `question_type`, `marks`, `negative_marks`, `correct` (JSON list), `position`.
   - Constraints: `UniqueConstraint(fields=['quiz', 'position'])`.
5. **QuizOption** (`quiz_option`):
   - Fields: `question_id`, `option_id`, `option_text`.
   - Constraints: `UniqueConstraint(fields=['question', 'option_id'])`.
6. **QuizAttempt** (`quiz_attempt`):
   - Fields: `id`, `quiz_id`, `student_id`, `status` (STARTED, SUBMITTED), `deadline_at`, `seed`, `question_order` (JSON list), `tab_violations`, `submitted_at`, `created_at`.
   - Constraints:
     - `UniqueConstraint(fields=['quiz', 'student_id'], condition=Q(status='STARTED'))` (only 1 active attempt at a time).
7. **AttemptResponse** (`quiz_attempt_response`):
   - Fields: `attempt_id`, `question_id`, `answer` (JSON), `saved_at`.
   - Constraints: `UniqueConstraint(fields=['attempt', 'question'])`.
8. **ResponseEvaluation** (`quiz_response_evaluation`):
   - Fields: `response_id`, `status` (PENDING, AI_SUGGESTED, FINAL), `auto_marks`, `final_marks`, `feedback`, `finalized_by`.
9. **QuizResult** (`quiz_result`):
   - Fields: `attempt_id`, `status` (NOT_EVALUATED, PARTIALLY_EVALUATED, EVALUATED, RELEASED), `marks_obtained`, `percentage`, `passed`.
10. **AuditLogEntry** (`quiz_audit_log`):
    - Append-only event log. `save()` on existing pk and `delete()` raise `ValueError`.
11. **Notification** (`quiz_notification`):
    - Fields: `recipient_user_id`, `event`, `payload`, `delivery_status`, `created_at`.

---

## 3.3 (c) Declarative State Machines

### 1. Quiz Lifecycle Machine (M1)
| Current State | Action | Actor | Guard | Next State | BRs Covered |
|---|---|---|---|---|---|
| DRAFT | configure | PROFESSOR | True | DRAFT_CONFIGURED | BR-005 |
| DRAFT_CONFIGURED | prepare | PROFESSOR | True | READY_TO_PUBLISH | BR-005 |
| READY_TO_PUBLISH | publish | PROFESSOR | owns_course && questions_valid && config_valid | SCHEDULED (if start > now) else AVAILABLE | BR-002, BR-005, BR-006 |
| SCHEDULED | boundary_start | SYSTEM | now >= start_at | AVAILABLE | BR-006, BR-018 |
| AVAILABLE | boundary_close | SYSTEM | now >= close_at | CLOSED | BR-006, BR-018 |
| CLOSED | archive | PROFESSOR | archive_permitted (no active attempts) | ARCHIVED | BR-023 |
| (DRAFT, DRAFT_CONFIGURED, READY_TO_PUBLISH) | edit | PROFESSOR | owns_course | Preserves current state | BR-002, BR-005 |

### 2. Student Attempt Machine (M2)
| Current State | Action | Actor | Guard | Next State | BRs Covered |
|---|---|---|---|---|---|
| (None) | start | STUDENT | quiz_is_available && within_window && attempts_remaining | STARTED | BR-003, BR-006, BR-007, BR-008 |
| STARTED | save_response | STUDENT | within_deadline && navigation_permitted | STARTED | BR-010, BR-015 |
| STARTED | tab_violation | SYSTEM/STUDENT | tab_count < limit | STARTED | BR-013 |
| STARTED | tab_violation | SYSTEM/STUDENT | tab_count >= limit | SUBMITTED | BR-013, BR-016 |
| STARTED | submit | STUDENT | within_deadline && (unanswered_allowed || all_answered) | SUBMITTED | BR-007, BR-012, BR-016 |
| STARTED | auto_submit | SYSTEM | now >= deadline_at | SUBMITTED | BR-007, BR-017 |

### 3. Result & Evaluation Machine (M3)
| Current State | Action | Actor | Guard | Next State | BRs Covered |
|---|---|---|---|---|---|
| (On Attempt Submit) | init | SYSTEM | attempt.status == SUBMITTED | NOT_EVALUATED | BR-018, BR-020 |
| NOT_EVALUATED | auto_evaluate | SYSTEM | all_objective_questions | EVALUATED | BR-018, BR-020 |
| NOT_EVALUATED | auto_evaluate | SYSTEM | has_subjective_questions | PARTIALLY_EVALUATED | BR-018, BR-019 |
| PARTIALLY_EVALUATED | finalize_subjective | PROFESSOR | all_responses_graded | EVALUATED | BR-019, BR-020 |
| EVALUATED | release | PROFESSOR | owns_course && release_permitted | RELEASED | BR-021 |

---

## 3.4 (d) Permission List & IAM Grants

```python
MODULE = "quiz"

PERMISSIONS = [
    # Faculty permissions
    "quiz.quiz.create",
    "quiz.quiz.view",
    "quiz.quiz.update",
    "quiz.quiz.delete",
    "quiz.quiz.publish",
    "quiz.quiz.archive",
    "quiz.question.manage",
    "quiz.evaluation.grade",
    "quiz.result.release",
    "quiz.report.view",
    # Student permissions
    "quiz.attempt.start",
    "quiz.attempt.submit",
    "quiz.attempt.view",
    "quiz.result.view",
]

ROLE_GRANTS = {
    "faculty": [
        "quiz.quiz.create",
        "quiz.quiz.view",
        "quiz.quiz.update",
        "quiz.quiz.delete",
        "quiz.quiz.publish",
        "quiz.quiz.archive",
        "quiz.question.manage",
        "quiz.evaluation.grade",
        "quiz.result.release",
        "quiz.report.view",
    ],
    "student": [
        "quiz.quiz.view",
        "quiz.attempt.start",
        "quiz.attempt.submit",
        "quiz.attempt.view",
        "quiz.result.view",
    ],
}
```

---

## 3.5 (e) Endpoint List

All endpoints prefixed with `/api/v1/quiz/`:

| Method | Path | Required Permission | Gate / Scoping | Description | Rule IDs |
|---|---|---|---|---|---|
| GET | `/quizzes/` | `quiz.quiz.view` | Faculty sees course quizzes; Student sees available quizzes | List quizzes | BR-002, BR-003, UC-007 |
| POST | `/quizzes/` | `quiz.quiz.create` | Faculty only | Create draft quiz | BR-001, UC-001 |
| GET | `/quizzes/{id}/` | `quiz.quiz.view` | Scoped by course/eligibility | Get quiz details | BR-002, BR-003, UC-007 |
| PUT/PATCH | `/quizzes/{id}/` | `quiz.quiz.update` | Course owner, pre-activation | Update quiz | BR-002, BR-005, UC-001 |
| DELETE | `/quizzes/{id}/` | `quiz.quiz.delete` | Course owner, closed/draft | Delete/archive quiz | BR-023, UC-006 |
| POST | `/quizzes/{id}/publish/` | `quiz.quiz.publish` | Course owner | Publish / Schedule quiz | BR-005, BR-006, UC-005 |
| POST | `/quizzes/{id}/archive/` | `quiz.quiz.archive` | Course owner | Archive closed quiz | BR-023, UC-006 |
| GET | `/quizzes/{id}/questions/` | `quiz.question.manage` | Course owner | List quiz questions | BR-005, UC-002 |
| POST | `/quizzes/{id}/questions/` | `quiz.question.manage` | Course owner, pre-activation | Add question to quiz | BR-005, UC-002 |
| GET | `/question-bank/` | `quiz.question.manage` | Faculty only | Search & filter question bank | UC-003 |
| POST | `/question-bank/` | `quiz.question.manage` | Faculty only | Add item to question bank | UC-003 |
| POST | `/quizzes/{id}/start/` | `quiz.attempt.start` | Student eligible, within window | Start attempt | BR-003, BR-006, BR-008, UC-008 |
| GET | `/attempts/{id}/` | `quiz.attempt.view` | Student (own) / Faculty | View attempt state & questions | BR-004, UC-009 |
| POST | `/attempts/{id}/save/` | `quiz.attempt.start` | Student (own), active | Save answer | BR-010, BR-015, UC-009 |
| POST | `/attempts/{id}/violation/` | `quiz.attempt.start` | Student (own), active | Record tab violation | BR-013 |
| POST | `/attempts/{id}/submit/` | `quiz.attempt.submit` | Student (own), active | Submit attempt | BR-012, BR-016, UC-010 |
| GET | `/quizzes/{id}/submissions/` | `quiz.evaluation.grade` | Course owner | List submissions | UC-016 |
| POST | `/responses/{id}/grade/` | `quiz.evaluation.grade` | Course owner | Grade subjective response | BR-019, UC-013 |
| POST | `/quizzes/{id}/release-results/`| `quiz.result.release` | Course owner | Release results | BR-021, UC-014 |
| GET | `/quizzes/{id}/results/` | `quiz.result.view` | Student (released) / Faculty | View quiz results | BR-004, BR-021, UC-015 |
| GET | `/quizzes/{id}/reports/` | `quiz.report.view` | Course owner | Performance analytics | UC-016 |

### Client Sidebar Entry (`Fusion-client`):
```json
{
  "id": "quiz",
  "label": "Quizzes",
  "icon": "Exam",
  "to": "/quiz",
  "section": "Academics"
}
```

---

## 3.6 (f) Contracts

`modules/quiz/contracts.py`:
- `get_student_quiz_summaries(student_ids: Sequence[int]) -> list[dict]`: Plural getter for student assessment history across all quizzes.
- `get_course_quiz_summaries(course_ids: Sequence[int]) -> list[dict]`: Plural getter for course quiz counts, active quizzes, and completion rates.

---

## 3.7 (g) Scheduled Work

`modules/quiz/schedule.py`:
- `check_quiz_availability_boundaries`: Every 1 minute. Moves `SCHEDULED` quizzes to `AVAILABLE` when `start_at <= now`, and `AVAILABLE` quizzes to `CLOSED` when `close_at <= now`.
- `auto_submit_expired_attempts`: Every 1 minute. Auto-submits any active attempt where `deadline_at <= now`.

---

## 3.8 (h) Open Questions

1. **AI Subjective Scoring Engine**: The specification mentions AI suggested marks for short/long answers. In the absence of an external LLM microservice connection, the engine provides an internal deterministic semantic heuristic and leaves final sign-off to the Professor (as strictly mandated by BR-QZ-019).
2. **Photo upload for questions**: File uploads are supported via Django standard media handling (`upload_to="quiz/question-bank/"`).

