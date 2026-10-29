# ELM Phase 2 — Implementation Progress

## Checkpoint 1: API ownership and access control

**Status:** Implemented and tested

### Changes made

- Added the ELM API router registration with an explicit `basename="leave"`.
- Updated the leave serializer so the employee ID and status are read-only.
- Added authenticated employee ownership to leave creation.
- Scoped employee self-service queries to the authenticated IAM principal.
- Added permission checks for ELM module access and leave operations.
- Added the initial ELM API test suite.

### Problems identified in the earlier implementation

- The API exposed leave records without adequate ownership protection.
- The client could potentially attempt to assign a leave request to another employee.
- The ELM router could not infer its basename after the viewset began using a dynamic queryset.
- The leave model still contained placement-specific status values.
- Generic update and delete endpoints could bypass the intended leave workflow.

### Verification evidence

Commands run:

```bash
python manage.py check
python manage.py permission_manifest
python manage.py permission_manifest --check
python manage.py showmigrations elm
python manage.py makemigrations --check --dry-run
pytest modules/elm/tests/test_api.py -q
```

Results:

- Django system check: no issues.
- Permission manifest: matches the registries.
- ELM migration `0001_initial`: applied.
- Migration check: no changes detected.
- ELM API tests: 4 passed.

### Remaining work

- Replace placement-specific statuses with leave-specific states.
- Implement the leave approval and sanction workflow.
- Implement cancellation, extension, and resumption.
- Add workflow and authorization tests.
- Verify the complete module and document final evidence.