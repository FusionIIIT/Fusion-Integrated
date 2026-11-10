# Assignment 7 submission

## Submission branches

- Base repository: `FusionIIIT/Fusion-Integrated`
- Base branch: `main`
- Head repository: `sachinrathod11/Fusion-Integrated`
- Head branch: `assignment-7/leave-management`

The existing environment had no uncommitted changes when submission preparation
began, so no stash or stash pop was needed. The tested Assignment 6B implementation
was already committed on the fork's main branch. This module branch retains that
implementation and adds the submission notes; it preserves the other existing
ELM branches without replacing their distinct work.

## Suggested PR title

Assignment 7: integrate Employee Leave Management

## Suggested PR description

Integrates the supplied Employee Leave Management implementation with the Fusion
module registry, IAM permission declarations, React navigation, Django APIs,
PostgreSQL migrations, and Celery schedules. Employees can apply for leave and
use the substitute, review, cancellation, extension, and resumption workflows;
administrators can manage policies, calendars, hierarchy, and balance records.

Includes fixes preventing indirect organizational hierarchy cycles and balance
corrections that consume days reserved by pending requests, with four regression
tests. The original uploaded ZIP is preserved separately.

Validation completed on the implementation commit:

- Backend: 546 tests and `make check` checks passed with test settings.
- Frontend: 37 tests, TypeScript checking, and production build passed.
- Leave migration and policy/module seed commands completed.
- Runtime readiness reports database, cache, and broker healthy.
- Anonymous Leave API access through the Vite proxy returns HTTP 401.

Known gaps: live IAM login and institute-specific calendars/hierarchy/authorities
need configuration; full ELM specification compliance remains unverified. The
complete specification package was not supplied to this implementation session.
Qwen 2.5:8b was reported as the original model but was unavailable here; this
session's changes were made using the current assistant. See
`docs/08-delivery/assignment-6b-review.md` for evidence and limitations. Blueprint
and specification-folder links must be supplied before claiming specification
traceability. This PR does not claim the full deployment definition of done.

## Open the PR

Use this comparison with the head and base already selected:

https://github.com/FusionIIIT/Fusion-Integrated/compare/main...sachinrathod11:Fusion-Integrated:assignment-7/leave-management?expand=1

GitHub API access is blocked in this execution environment, so an actual PR
number/link could not be created automatically. After opening the PR, copy its
`https://github.com/FusionIIIT/Fusion-Integrated/pull/<number>` URL and submit it
in the assignment form:

https://forms.gle/gpZ5r4hmNNC3QCMq8

The compare URL is not a PR URL and should not be submitted in its place.
