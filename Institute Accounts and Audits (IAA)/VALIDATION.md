# IAA verification evidence

Validation performed in the current cloud environment on 10 November 2026.
Synthetic identities and configured fixture amounts are test data, not institute
policy values or real financial records.

| Check | Result |
| --- | --- |
| `DJANGO_SETTINGS_MODULE=config.settings.test make check` | Passed; all 611 backend tests executed, including 65 IAA tests |
| Django system checks | Passed |
| Model/migration consistency | No changes detected |
| Ruff | Passed |
| Import boundaries | Six contracts kept, zero broken |
| Cross-module foreign keys | None |
| Batched public contracts | Passed |
| Navigation and client-route parity | Passed |
| Generated permission manifest | Current |
| OpenAPI generation and committed-schema comparison | Passed with warnings treated as errors |
| `make check-client` | Typecheck passed; 44 tests in six files passed; production build passed |
| Explicit real-browser smoke | One test passed; full expense lifecycle plus Fusion dashboard/bell notifications |
| Real concurrent budget validation | Passed; two competing requests cannot overreserve departmental budget |
| IAA migrations on development PostgreSQL | 0001, 0002, and 0003 applied successfully |
| `seed_modules` | IAA registered with the existing Placement and Leave modules |
| `run_iaa_escalations` | Completed; no current live requests to escalate |
| Original input document checksums | All six files match the uploaded ZIP exactly |
| `git diff --check` | Passed |

The browser test uses Chromium, the real Vite/React UI, Django's live test server,
and an isolated PostgreSQL test database. Only IAM is substituted. It creates an
expense draft, submits it, validates as Finance, approves as HoD/Dean/Director,
records internal completion as Finance, verifies the Fusion dashboard's recent
notifications, and opens the notification view using the shell bell. Browser
runtime errors are asserted absent.

The security tests include both Fusion permission gates, missing explicit
multi-role selection, forged role headers, revoked assignments, cross-user and
cross-department access, administrative operational separation, last-admin
protection, invalid evidence schemes, post-submission edit protection, required
decision remarks, observation evidence/verification, and PostgreSQL immutability.

The client build emits the existing advisory for the shared bundle exceeding
500 kB. The IAA workspace is split into a lazy-loaded module chunk. No failing
check was bypassed or disabled to obtain these results.

`evidence/` contains the final check logs and synthetic screenshots. Screenshot
dates inside the UI reflect the browser test's deliberately frozen fixture
date, not the validation date above.

## Assessment boundaries

These results establish the tested implementation and its integration in this
environment. They do not certify every possible institutional policy, external
document-storage access, live IAM interoperability, accessibility compliance,
production load, staging rollout, or independent mentor acceptance. See README
for setup requirements, document-reference handling, and the list-size limit.

No GitHub push, publication, PR creation, bank transfer, or offline model execution
is claimed for this IAA implementation task.
