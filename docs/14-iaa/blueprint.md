# IAA module blueprint

## Scope and conventions

- Module: Institute Accounts and Audits (IAA), code `iaa`; specification identifiers use `IAA-` prefixes.
- Implement in `modules/iaa`, `client/src/modules/iaa`, `client/e2e/iaa`, and `docs/14-iaa` (confirm numbered spec-folder convention against repository before writing code).
- Match the Fusion-Integrated `modules/placement` architecture, API conventions, RBAC, audit logging, notification/outbox, and client module registration patterns.
- No payment execution, bank integration, tax calculation, procurement, or external dependency.
- Keep all monetary thresholds and timeout durations configurable; do not embed policy values in code.
- Do not add spec tests or run tests in this implementation pass.

## Domain capabilities

1. Expense/voucher lifecycle: creator drafts, attachments, completeness checks, submission/locking, Finance validation and clarification, configured approval, internal recording.
2. Approvals: configured multi-level route based on amount, type, department and hierarchy; distinct HoD/Dean/Director roles; explicit active role; self-approval prevention; eligible-authority substitution; remarks and timeout escalation.
3. Budgets and anomalies: Finance budget validation; insufficiency creates reviewable anomaly rather than automatic rejection; manual Finance/Auditor and configured automatic anomaly creation; designated resolver; Open/Resolved/Escalated outcomes.
4. TA lifecycle: eligible employee submission with dates/purpose/amount/evidence; Finance verification and clarification; configurable high-value route; approved/verified internal recording and read-only terminal state.
5. Audit observations: Auditor reviews financial records, raises immutable-history observations; concerned party responds with corrective action/evidence; Auditor closes only satisfactory responses; unsatisfactory response returns to Open.
6. Reporting and notifications: scoped read-only dashboards/exports; own-record status/history; assignment-scoped notifications for lifecycle and pending/overdue events.
7. Administration: role assignment, hierarchy/thresholds, financial years and policy parameters; System Admin has configuration-only permissions and no operational financial-record access.
8. Cross-cutting: RBAC, segregation of duties, role-switch context, immutable historical attribution, and audit trail containing actor, active role, timestamp, action and resulting status where applicable.

## Proposed implementation shape

- `models/`: requests, supporting-document metadata, TA claims, approval routes/steps/actions, budget allocations, anomaly records, audit observations/responses, policy/configuration, audit events and notification/outbox records. Use explicit enums and timestamps; retain status/action history rather than overwriting it.
- `domain/`: explicit state machines and pure policy decisions for request/TA/observation/anomaly transitions, completeness, approval eligibility, routing, thresholds and escalation eligibility.
- `services/`: transactional use-case operations; enforce actor authorization and segregation of duties; write history/audit/outbox events atomically; no external financial side effects.
- `selectors/`: role- and ownership-scoped query paths for operational views, status tracking, dashboards and exports.
- `api/`: serializers, permissions, endpoints and URLs organized by request, TA, approval, anomaly, audit, reports and configuration capabilities. Apply pagination/filtering and the repository's response/error/status conventions.
- `management/` or Celery task: due-approval escalation and configured automatic anomaly evaluation, idempotently, using repository scheduling/outbox conventions.
- `client/src/modules/iaa/`: role-aware routes/pages and API hooks for drafts, submission, Finance queues, approval queues, TA, anomalies, audit observations, reports, notifications and configuration. Keep System Admin views configuration-only.
- Registration changes only where architecture requires: settings/URL inclusion, module/client registry, permissions manifest/OpenAPI generation, import boundaries. Review/approve any shared-file changes and new dependency before applying.
- `docs/14-iaa/`: blueprint, module quality report, and module-specific operational notes required by the canonical prompt; no spec-test artifacts in this implementation phase.

## Traceability and policy safeguards

- Map all 18 CFRs and 75 AFRs to a model/API/service/UI capability and persist their exact spec IDs in implementation documentation.
- Implement all 25 actor-triggered and 2 event-triggered use cases; preserve the 19 basis and 4 composite workflows, including all stated alternate/exception paths and terminal states.
- Treat authoritative state-transition tables and business rules as the implementation authority when choosing status changes. Do not invent monetary limits, timeout durations, approvers, payment behavior, or unsupported transitions.
- Preserve system-admin operational-data exclusion and Basic User ownership scoping on every query and action, not only UI visibility.

## Open decisions before implementation

- Confirm the correct assigned branch/module-code conventions and spec folder number; the supplied source directory is named `14-IAA`, so `14-iaa` is the working assumption.
- Resolve storage policy for uploaded evidence using repository-standard document storage; the specification requires attachments but does not prescribe a provider. Prefer existing Fusion document handling and do not add a new external service.
- Confirm the repository's scheduler/outbox pattern for due approvals and automatic anomaly checks before selecting task placement.
- Student 2 accepted this blueprint in chat on 2026-11-22. IAM role provisioning and host-project registration remain integration steps; they are not changes to the module package itself.

