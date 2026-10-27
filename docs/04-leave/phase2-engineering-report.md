# Employee Leave Management Phase 2 Engineering Report

## Baseline

Phase 1 is preserved at commit `4e40661` (`feat(leave): add self-service leave request foundation`). Phase 2 work is isolated on `phase2-elm-hardening`; no commit, push, PR, reset, clean, or force operation was performed. The pre-existing changes in `manage.py` and `ops/` remain outside this work.

## Architecture

ELM is an independent Django module. It owns `leave_request`, stores IAM-owned `user_id` values without cross-module foreign keys, applies IAM module and permission gates at the API boundary, scopes reads through selectors, and puts writes in services. The current client module is loaded from Fusion's server-driven registry and uses the existing Leave API only.

## Corrected defects

| Severity | Problem | Correction | Verification |
| --- | --- | --- | --- |
| High | Invalid CL half-day values were accepted by direct service callers. | Domain and database constraints restrict values to full, first, or second. | Domain/service tests pass. |
| High | Station Leave details were only checked by the serializer. | Shared service validation and database constraint enforce the relationship. | Domain/service tests pass. |
| High | Approved requests did not block overlaps. | Overlap now considers pending and approved requests. | API regression test added; database run pending. |
| High | Empty overlap queries had a concurrent-write race. | PostgreSQL transaction advisory locking serializes each employee's overlap check and insert. | Lock-path test passes; PostgreSQL concurrency test pending. |
| High | Leave was inaccessible through Fusion's UI. | Active module registry, filtered navigation, lazy client route, form, history, and withdrawal control added. | Typecheck and production build pass. |
| Medium | OpenAPI omitted Leave and schema generation failed. | Withdrawal response schema declared; generated OpenAPI committed. | Schema generation passes. |
| Medium | Django proposed an index rename. | Model retains the migration's explicit index name. | Migration check finds no changes. |

## Verification

| Command | Result |
| --- | --- |
| `python -m pytest modules/leave/tests/test_domain.py modules/leave/tests/test_services.py -q` | Pass: 13 tests; non-fatal pytest cache warning. |
| `python manage.py check` | Pass. |
| `python manage.py makemigrations --check --dry-run` | Pass with a warning that PostgreSQL at `127.0.0.1:5432` is unavailable. |
| `python manage.py spectacular --fail-on-warn --file openapi/fusion-integrated.v1.yaml` | Pass. |
| `npm run typecheck` | Pass. |
| `npm run build` | Pass, including the lazy Leave page chunk. |
| `npm test` | Not completed: Vitest worker startup hangs in this Windows environment. |

The virtual environment and lockfile-pinned client dependencies were restored without changing dependency manifests. The client audit reported 12 dependency findings (6 moderate, 4 high, 2 critical); no lockfile upgrade was made outside ELM scope.

## Remaining requirements and risks

The companion `phase2-traceability.md` records each specification requirement. The CL/RH self-service foundation is now safer and accessible in the client, but it is not full ELM. Missing active scope includes leave accounts and entitlements, RH/VL calendar integration, SCL/EL/COL/VL, counting rules, substitutes, hierarchy approvals, cancellation, extension, resumption, notifications/SLA, administration, offline synchronization, exports, and balance views.

Docker and PostgreSQL are unavailable, so full backend/API, migration application, runtime, and concurrent PostgreSQL verification remain unperformed. The module must not be assessed as deployment-ready against the complete ELM specification until its missing policy, calendar, organization, hierarchy, and leave-account contracts are implemented and verified.
