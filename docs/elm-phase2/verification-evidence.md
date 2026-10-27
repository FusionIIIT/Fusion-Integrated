# ELM Phase 2 — Verification Evidence

## Revision and preservation

- Phase-1 baseline: `d1cb96a` (preserved as the parent of Phase 2).
- Phase-2 implementation: `c3ab25c` on `elm-phase2`.
- Upstream pull request: [FusionIIIT/Fusion-Integrated#359](https://github.com/FusionIIIT/Fusion-Integrated/pull/359).

## Automated checks

Commands were run from the Fusion-Integrated repository root on 2026-10-27.

| Area | Command | Result |
|---|---|---|
| Backend regression suite | `.venv\Scripts\python.exe -m pytest -q` | Passed |
| Client typecheck | `cd client; npm run typecheck` | Passed |
| Client test suite | `cd client; npm test -- --run` | Passed, 4 files / 35 tests |
| Production client build | `cd client; npm run build` | Passed; Vite reported the existing >500 kB chunk warning |
| Django configuration | `.venv\Scripts\python.exe manage.py check` | Passed; no issues |
| Migration consistency | `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` | Passed; no changes detected |
| ELM migration application | `.venv\Scripts\python.exe manage.py migrate --noinput` | Passed; ELM migrations 0004 and 0005 applied to the configured local database |
| ELM static lint | `.venv\Scripts\ruff.exe check modules/elm` | Passed |
| OpenAPI generation | `.venv\Scripts\python.exe manage.py spectacular --fail-on-warn --file openapi/fusion-integrated.v1.yaml` | Passed |
| Patch whitespace | `git diff --check` | Passed before the Phase-2 commit |

## ELM behavior covered

`modules/elm/tests/test_leave_api.py` exercises employee ownership and permission
checks; staff/faculty submission; date validation; active-request overlap
rejection for pending and approved leave; no blocking from rejected leave;
the opposite-half single-day Casual Leave exception; invalid half-day use;
request immutability; pending-only withdrawal; and event history.

## Local runtime evidence and limitation

- The Vite frontend returned HTTP 200 on the local dev server.
- Django started successfully and passed `manage.py check`.
- An unauthenticated request to `/api/v1/elm/leave-requests/` returned HTTP 401,
  as expected for a protected API endpoint.
- Authenticated sign-in and end-to-end ELM use could not be verified because the
  app is configured to contact IAM at `http://127.0.0.1:8001`, and no IAM service
  was listening there during the local run. The separate Administration console
  is not a replacement ERP-user IAM service.

## Known warnings and boundaries

- `npm run build` succeeds but emits a Vite warning for the 502.55 kB main
  JavaScript chunk.
- The repository's client lint script was not part of this verification run;
  previously, it could not run because the `eslint` executable was unavailable.
- Automated tests and local API responses do not establish production IAM
  integration or full specification compliance.
