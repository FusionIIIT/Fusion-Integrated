# Initial environment and check observations

This is a hand-recorded summary, not a machine-generated pytest artifact.

- Docker Postgres startup failed because the Docker Desktop Linux engine pipe was not available.
- The first SQLite-backed PHC run failed during an unrelated placement migration: SQLite reported `no such index: document_profile_idx` while processing `DROP INDEX "document_profile_idx"`.
- The first permission-manifest check reported `registry/permissions.json is stale - run 'make permissions'`; PHC had no `modules/phc/registry.py` source.
- The first model/migration check proposed `0002_alter_prescription_expense_date.py` because the manually written migration help text differed from the model.
- The first import-boundary check reported `modules.phc.tests.test_uc -> modules.directory.models`; the test was changed to stub the directory module's public contract.

Final check logs are in `../../django-check.log`, `../../migration-check.log`, `../../permission-check.log`, and the other sibling result files. The local SQLite workaround is documented in `docs/09-phc/spec-tests/README.md`.
