# Employee Leave Management (ELM)

ELM is registered as an independent Fusion module (`elm`) and reuses Fusion authentication, the permission manifest, the module registry, and the shared React shell.

## Initial API
- `GET /api/v1/elm/mine`
- `POST /api/v1/elm/apply`
- `POST /api/v1/elm/requests/<id>/action` (`withdraw`, `accept_substitute`, `decline_substitute`, `approve`, `not_recommended`, `final_approve`, `final_reject`)
- `GET /api/v1/elm/accounts`
- `GET /api/v1/elm/approvals`
- `GET /api/v1/elm/substitute-requests`
- `GET/POST /api/v1/elm/policies`

## Local integration
1. Apply migrations: `python manage.py migrate`.
2. Seed modules/navigation: `python manage.py seed_modules`.
3. Seed permission manifest according to the existing IAM procedure; assign ELM permissions to institute designations in the IAM environment.
4. Run backend and frontend checks.

## Important implementation gaps before production/PR acceptance
This is an initial integration implementation, not a claim of full conformance to ELM synchronized v1.4/v1.6. It does not yet implement every UC/BR or workflow: cancellation, extension, resumption, year-end transactions, leave accrual/entitlement initialization, holiday/RH/VL calendar integration, Station Leave validations, configured Establishment routing, SLA reminders/escalations, Director-specific routing, policy administration validation, exports/print, and comprehensive audit/event history. Permission role grants are a provisional mapping and must be aligned to IAM designations. The approval list currently requires review permission and needs explicit Unit Head/final-authority scoping. Add tests for each complete Basis Workflow and Composite Workflow in the authoritative v1.6 STT before representing the module as complete.
