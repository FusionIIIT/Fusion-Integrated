TITLE: Regenerate the permission manifest, its catalog doc and the OpenAPI schema
FORMAT: whole
EDIT: modules/leave/__init__.py
LIMIT: 300
POST: permissions schema
---
Fusion's CI checks that three committed, tool-generated files match the code: registry/permissions.json and docs/02-iam/permission-catalog.generated.md (from `manage.py permission_manifest`, i.e. `make permissions`) and openapi/fusion-integrated.v1.yaml (from `manage.py spectacular`, i.e. `make schema`). The task runner regenerates them with those tools right after this step, so no code change is needed from you.

Your only job: keep modules/leave/__init__.py exactly as it is now (output its current content unchanged).
