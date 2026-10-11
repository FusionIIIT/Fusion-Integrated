# Employee Leave Management (ELM)

Initial Fusion-Integrated backend module scaffold for ELM. It follows the repository's module layout, uses IAM user IDs as integer references (no cross-module foreign keys), and exposes API routes under `/api/v1/elm/`.

## Integration

- Django app: `modules.elm`
- URL mount: `config/urls.py`
- Module registration: `config/settings/base.py` and `registry.py`
- Migration: `migrations/0001_initial.py`

The current implementation provides the initial data model and API skeleton for leave requests, approval tasks, leave balances, policies, published calendar days, and resumption records. It is not a complete implementation of every BR/UC/WF in the specification bundle; workflow authority resolution, full leave policy calculations, SLA processing, offline synchronization, cancellation/extension flows, and client pages still need to be completed from the synchronized specifications. Permission codes also need to be granted by the IAM configuration for the institute's actual roles.
