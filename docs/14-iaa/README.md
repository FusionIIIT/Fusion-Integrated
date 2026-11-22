# Internal Audits and Accounts (IAA)

The IAA bounded context records institute expense requests, travel claims, Finance review, configured approvals, audit observations, anomaly follow-up, reports, and notifications. It does not execute payments or transfer funds.

## Implementation

- `modules/iaa/` owns its models, migrations, selectors, transactional services, API, permission declarations, and workflow rules.
- `client/src/modules/iaa/` contains the IAA routes, pages, and calls through Fusion's CSRF-aware HTTP client.
- The module is registered in `DOMAIN_MODULES`, `/api/v1/iaa/`, the client module registry, and `.importlinter`.
- `traceability.md` maps the supplied CFR/AFR requirements and use cases to implementation areas. `blueprint.md` records Student 2's acceptance.

## Deployment follow-up

1. Generate and review the repository's permissions manifest and OpenAPI schema; seed the approved IAA grants in Fusion IAM.
2. Provision the IAA designations in IAM. The code includes `Basic User`, `Finance Staff`, `Auditor`, `System Admin`, Director, Dean, and HoD grants; exact institute designation names must match `modules/iaa/registry.py`.
3. Configure the IAA policy, departmental budgets, and approval routes before Finance validation begins.
4. Schedule `iaa.escalate_overdue_approval_steps` through the deployment's Celery beat configuration and connect notification delivery if messages should leave the IAA dashboard feed.
5. Apply the included module migrations through the host's normal deployment process.

Evidence is represented by owner-scoped Google Drive links validated through Fusion's shared file helpers. No file bytes are uploaded by this module. User identities remain integer references supplied by IAM.

No tests were run for this change, per the task request.
