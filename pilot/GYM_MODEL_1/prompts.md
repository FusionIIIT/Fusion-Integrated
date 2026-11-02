# Trial 1 — Prompts & Interaction Log (Qwen2.5-Coder:7b + Continue)

## Prompt 1 — Codebase and Architecture Inspection
```text
@codebase what modules exist under modules/ and what are the main architectural rules for adding a new module?
```
- **Observation**: In Continue's Agent mode, the model outputted raw tool-call JSON text `{"name": "ls", "arguments": {"dirPath": "modules/"}}` instead of running actions directly. Switched Continue to Chat mode. The model then correctly identified `accesscontrol`, `directory`, and `placement`, noting the pure-Python domain rule and the no cross-module foreign key rule (ADR-0013).

## Prompt 2 — Module Registration
```text
@file modules/placement/apps.py @file modules/placement/registry.py
Look at how placement is registered. Write apps.py and registry.py for gymkhana with 9 navigation items and role grants for student, club_coordinator, student_admin, and faculty.
```
- **Observation**: Outputted `apps.py` and `registry.py` cleanly. Permission strings were properly prefixed (`gymkhana.club.view`, `gymkhana.membership.apply`, `gymkhana.booking.manage`, etc.) matching the specification sheet.

## Prompt 3 — ORM Models
```text
@file specs/gymkhana/05_requirements_registry.md
Write the Django models for modules/gymkhana/models.py.
Include Club, ClubLeadership, ClubMembership, VenueBooking, VotingPoll, PollOption, PollVote, ClubBudgetRequest, and ClubEventReport.
Important: Do not use foreign keys to auth.User or other apps. Use integer IDs like coordinator_id and student_id.
```
- **Observation**: The model generated all 9 models with correct field types. It initially forgot `unique_together` on ClubMembership `('club', 'student_id')` and PollVote `('poll', 'student_id')`, which I added during manual inspection.

## Prompt 4 — Domain Business Rules
```text
@file specs/gymkhana/01_business_rules.md
Write modules/gymkhana/domain/policy.py implementing pure python validation functions for the business rules. Do not import Django, models, or DRF. Return tuple of (bool, str) for validation results.
```
- **Observation**: Generated the pure Python validators for club categories, booking time range (`start_time < end_time`), cross-type venue conflict check, and poll eligibility. Handled Decimal comparison for budget amounts properly without importing any Django modules.

## Prompt 5 — Application Services
```text
@file modules/gymkhana/models.py @file modules/gymkhana/domain/policy.py
Write modules/gymkhana/services/applications.py with transactional service functions for club creation, confirmation, venue booking, membership application, and poll voting. Call the policy functions before saving.
```
- **Observation**: Service functions were wrapped in `@transaction.atomic`. Model queries and error handling with `ValueError` and `PermissionError` matched the use case flow.

## Prompt 6 — API Views and URLs
```text
@file modules/gymkhana/services/applications.py
Create serializers.py, views.py, and urls.py for gymkhana under modules/gymkhana/api/. Use HasModuleGrant('gymkhana') and HasPermission permissions from fusion_auth.
```
- **Observation**: Generated the DRF views and URL routes. During testing, noticed that `request.user` in Fusion can be either a custom Principal or standard user object, so I added a `_get_user_id(request)` helper to extract `user_id` safely.
