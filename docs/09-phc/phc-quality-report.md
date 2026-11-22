# PHC quality report

Base: `upstream/main` at `5595be6`. Every result below was observed on 2026-11-23, after the last
code change. Items marked NOT RUN are listed with the reason; nothing is claimed that was not seen.

Local test note: this machine's PostgreSQL `template1` has a stale collation version, so test
databases were created from `template0` through a settings override kept outside the repository
(`TEST = {"TEMPLATE": "template0"}` on top of `config.settings.test`). No repository file was changed
for it, and PostgreSQL's own templates were not altered.

## 1. `make check` and `make check-client`

| Step | Result |
|---|---|
| `manage.py check` | System check identified no issues (0 silenced). |
| `makemigrations --check --dry-run` | No changes detected |
| `ruff check .` | All checks passed! |
| `lint-imports` | Contracts: 5 kept, 0 broken. (includes `Layering inside phc`) |
| `ops/checks/no_cross_module_fk.py` | exit 0 |
| `ops/checks/contracts_are_plural.py` | exit 0 |
| `ops/checks/nav_matches_routes.py` | nav items and client routes agree |
| `permission_manifest --check` | permission manifest matches the registries |
| `make schema-check` | openapi schema matches the code |
| `pytest` (whole repository) | 786 passed, 27 subtests passed in 84.26s |

`make check-client`: exit 0 (`tsc` for the app and `e2e/`, `Tests 91 passed (91)`, build succeeds;
PHC page chunks total about 12 kB gzip).

## 2. Coverage

```
.venv/bin/pytest modules/phc --cov=modules/phc --cov-branch --cov-report=term-missing --cov-fail-under=90
TOTAL   1236   3   152   1   99%
Required test coverage of 90% reached. Total coverage: 99.71%
361 passed

.venv/bin/pytest modules/phc --cov=modules/phc/domain --cov-branch --cov-report=term-missing --cov-fail-under=95
TOTAL   142   0   32   0   100%
Required test coverage of 95% reached. Total coverage: 100.00%
361 passed
```

Uncovered: `api/views.py` 189 and 306 (an empty `ids` list after parsing, and the fallback branch of
`get_permissions` for an unmapped method) and `selectors/scoping.py` 85 (the empty-queryset return
for an actor with no requisition permission reaching the selector, which the view gate prevents).

## 3. Test counts

| File | Tests |
|---|---|
| test_state_machine.py | 162 |
| test_privilege_escalation.py | 92 |
| test_journeys.py | 44 |
| test_domain.py | 19 |
| test_refusals.py | 11 |
| test_patient_isolation.py | 9 |
| test_registry.py | 8 |
| test_audit_and_policy.py | 5 |
| test_query_budgets.py | 5 |
| test_client_route_guards.py | 3 |
| test_concurrency.py | 2 |
| test_schedule.py | 1 |
| **Total** | **361, all passing** |

Journey tests are named for their use cases: every live `PHC-UC-` main flow and every A/E flow the
spec names has one (`test_journeys.py`). Every one of the 90 live CFR, AFR, UC, BR and workflow ids is
cited by at least one test.

## 4. Rules broken on purpose (Step 5.15)

Each file was copied outside the repository, broken, the PHC suite run, then copied back; `cmp`
confirmed each restore and the suite returned to 361 passed.

| Rule broken | Change | Caught by (examples) |
|---|---|---|
| PHC-BR-02 scoping | patient visit filter removed | `test_patient_cannot_list_or_open_anothers_record_phc_br_02`, `test_phc_uc_02_e1_another_patients_record_is_denied` |
| PHC-BR-03 permission gate | `HasPermission` dropped from `_Gates` | `test_module_grant_without_permission_is_403[...]`, `test_role_switch_gives_only_the_acting_roles_view` |
| PHC-UC-09 E1 stock limit | negative stock allowed | `test_stock_cannot_go_negative_or_change_by_zero`, `test_phc_uc_09_e1_invalid_adjustment_is_rejected` |
| PHC-BR-08 transition | acting office ignored in `resolve` | `test_every_claim_move_outside_the_table_is_refused_cw_phc_01[...]` |
| PHC-BR-07 threshold | `<` changed to `<=` | `test_low_stock_is_strictly_below_threshold_phc_br_07[50-50-False]`, `test_phc_uc_09_a1_not_below_threshold_raises_nothing` |

## 5. Adversarial pass (Step 5.11)

| Question | Finding | Change |
|---|---|---|
| Can an approver approve their own record? | An office could act on its own claim | Scoping hides it (404); a claimant acting on their own claim is 403 `own_claim` |
| Can a thing appear in its own approval queue? | Claims and requisitions | `claims_for` and `requisitions_for` exclude the caller's own rows |
| Can a balance go negative? | Stock could | Refused in `rules.apply_stock_change` and by a CHECK constraint; a concurrency test runs three deductions at once |
| Can something be back-dated without limit? | Expense dates | Bounded by the PHC-BR-06 window; future dates refused |
| Can staff fabricate their own prescription to claim against? | Yes, in the earlier draft | Recording a visit for yourself is refused, also as a CHECK constraint |
| Can a closed or rejected record change? | No | Terminal states have no outgoing rows; a trigger freezes claim fields |
| Can one request take effect twice? | Concurrent transitions | `select_for_update` in each choke point; `test_concurrency.py` passes |

The refusal tests also found a real defect: `StockAdjustment.__str__` crashed when `delta` was not
yet a number. Fixed.

## 6. Security self-audit (Step 7.7)

- Both gates on every view (`_Gates.get_permissions`); `test_privilege_escalation.py` proves 401, and
  403 for each gate separately, on all 28 method/path pairs.
- Serializers list `fields` explicitly; server-owned fields are read-only.
- Every list and detail read starts from `selectors/scoping.py`; body ids are checked against scope
  or existence before use.
- No raw SQL on request data; the only SQL is the trigger migration.
- No file uploads.
- Every write is throttled (`phc_write`); `test_write_endpoints_are_throttled` sees a 429.
- A cookie-authenticated write without `X-CSRF-Token` is 403 (`test_cookie_write_without_csrf_header_is_403`).
- No log lines added; error envelopes carry no stack trace.
- Deploy check with production settings: `System check identified no issues (2 silenced).`
- No new Python or npm dependency.

## 7. Fresh install (Step 7.8)

Run on a throwaway database, `fusion_integrated_fresh`, with `DB_NAME` set on every command.
Docker is not installed on this machine, so the database was created through Django's connection
instead of `docker compose exec db createdb`.

```
$ create fusion_integrated_fresh (from template0)            created
$ make migrate                                              ... Applying placement.0010_retire_resume_documents... OK
$ manage.py migrate phc zero                                Unapplying phc.0002_append_only_triggers... OK
                                                            Unapplying phc.0001_initial... OK
$ make migrate                                              Applying phc.0001_initial... OK
                                                            Applying phc.0002_append_only_triggers... OK
$ manage.py seed_modules                                    phc: registered but NOT active — 1 prerequisite(s) unmet:
                                                              No reimbursement submission window is in effect (PHC-BR-06). ...
$ manage.py phc_readiness                                   CommandError: PHC is not ready: resolve the items above.
$ manage.py phc_configure_window --days 30 --includes-last-day yes   (placeholder; real value is open question 1)
                                                            Submission window set: 30 days from 2026-11-23
$ manage.py seed_modules                                    registered phc (active)
$ manage.py phc_readiness                                   PHC is ready.
stored Module(phc).status                                   active
```

NOT RUN: `seed_iam_permissions --manifest registry/permissions.json` in `Fusion_System_Administrator`,
granting a test account its role, and the first user action in the browser on the fresh database.
They change the IAM's database and need a person at the browser.

## 8. Browser walkthrough and Playwright (Step 6.9)

NOT RUN. `client/e2e/phc/` has the student journeys (`patient-pages.spec.ts`) and the deep-link check
for every guarded office page (`office-pages.spec.ts`); both typecheck. The office-role journeys still
need `client/e2e/accounts.ts` entries, whose role names must be read from the IAM. Running `make e2e`
needs the IAM on port 8001, a seeded IAM and `make dev`.

## 9. Scheduled tasks

None exist.

## 10. Accepted known gaps

None accepted yet. Open questions are in the blueprint's Step 3.8.

## 11. Approvals

- Blueprint: approved in writing by Student 2 (Kousik) on 2026-11-23, typed by Student 2 into
  Student 1's builder chat: "I have read docs/09-phc/phc-blueprint.md (PHC module, Assignment 9)
  against the PHC specification, and I approve it, including its open questions in Step 3.8."
  Earlier the same day Student 1 had relayed "fine you can start the code generation" from
  Student 2; that relay predates this blueprint version and is superseded by the written approval.
- Open questions 1–6 of the blueprint's Step 3.8 are covered by that approval.
- Shared files: only the registration lines Step 4.0 pre-approves, plus regenerated files and
  `ops/docs/phc_reference.py` (Step 7.6).
- Dependencies: none.

## 12. Review rounds

None yet.
