"""Reversible permission-negative browser fixtures require an explicitly synthetic IAM."""

import json
import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from iam.models import IamDesignationModule, RolePermission

if os.environ.get("HREIS_E2E_IAM_SYNTHETIC") != "1" or not settings.DEBUG:
    raise RuntimeError("Permission fixtures require a development synthetic IAM opt-in.")
snapshot = Path(os.environ["HREIS_E2E_PERMISSION_SNAPSHOT"]).resolve()
if snapshot.name != "iam-staff-permissions.json":
    raise RuntimeError("Unexpected fixture snapshot path.")
operation = os.environ["HREIS_E2E_PERMISSION_OPERATION"]
with transaction.atomic():
    rows = RolePermission.objects.filter(designation="staff", permission__startswith="hreis.")
    if operation == "remove":
        if snapshot.exists() or not rows.exists():
            raise RuntimeError("Restore an earlier snapshot before creating a new fixture.")
        if not IamDesignationModule.objects.filter(
            designation="staff", module_code="hreis"
        ).exists():
            raise RuntimeError("The module grant must remain independently present.")
        snapshot.write_text(json.dumps(list(rows.values("designation", "permission"))))
        rows.delete()
    elif operation == "restore":
        if snapshot.exists():
            original = json.loads(snapshot.read_text())
            rows.delete()
            RolePermission.objects.bulk_create([RolePermission(**row) for row in original])
            transaction.on_commit(snapshot.unlink)
    else:
        raise RuntimeError("Unknown fixture operation.")
