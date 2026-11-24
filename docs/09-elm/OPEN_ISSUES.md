# OPEN ISSUES.md

## Executive Summary

All automated tests pass (28 backend, 35 frontend, 408 platform). Zero critical or blocking defects in the ELM codebase.

## Resolved Issues

- **ISSUE-ELM-001**: u9001 and u9005 missing IAM designation assignments. Resolved via `assign_role`.
- **ISSUE-ELM-004**: IAM stale role refresh overwrite on pilot users. Resolved via setting `IAM_REFRESH_ROLES_AFTER_SECONDS=0` in development.
- **ISSUE-ELM-005**: Ruff linting and blind exception in test suite. Resolved with Http404 assertion and clean PEP 8 imports.

## Conditional / External Items

- **ISSUE-ELM-006**: Production IAM Role Synchronization (CONDITIONAL: `IAM_REFRESH_ROLES_AFTER_SECONDS=0` is a local development workaround; real institute deployment requires ERP GlobalsHoldsdesignation sync).
- **ISSUE-ELM-007**: Background SLA and Year-End Job Scheduling (EXTERNAL: Celery beat / cron scheduling required in production environment).

## Informational Issues

- **ISSUE-ELM-002**: Historical 289-Test Investigation (INFORMATIONAL: Investigated repository history; no artifacts found; verified fresh baseline of 28 backend, 35 frontend, and 408 platform tests established).