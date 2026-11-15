"""Verification tests for BR-SA-026: Boundary Protection & Operational Data Isolation.

Traceability: CFR-SA-020, AFR-SA-072, BR-SA-026.
"""
from __future__ import annotations

import pytest
from rest_framework.exceptions import PermissionDenied

from modules.system_admin.api.permissions import (
    FORBIDDEN_OPERATIONAL_PATTERNS,
    EnforceDataIsolationBoundary,
)


def test_isolation_boundary_blocks_prohibited_paths(rf):
    """BR-SA-026: Prohibited paths containing operational keywords must be blocked."""
    perm = EnforceDataIsolationBoundary()

    for pattern in FORBIDDEN_OPERATIONAL_PATTERNS:
        req = rf.get(f"/api/v1/system_admin/{pattern}/")
        with pytest.raises(PermissionDenied, match="is prohibited"):
            perm.has_permission(req, None)


def test_isolation_boundary_blocks_prohibited_query_params(rf):
    """BR-SA-026: Query parameters containing operational keywords must be blocked."""
    perm = EnforceDataIsolationBoundary()

    for pattern in FORBIDDEN_OPERATIONAL_PATTERNS:
        req = rf.get(f"/api/v1/system_admin/users/?{pattern}=true")
        with pytest.raises(PermissionDenied, match="is prohibited"):
            perm.has_permission(req, None)


def test_isolation_boundary_allows_administrative_queries(rf):
    """Allows standard administrative paths and safe filtering."""
    perm = EnforceDataIsolationBoundary()

    req1 = rf.get("/api/v1/system_admin/users/?department=CSE&batch_year=2026")
    assert perm.has_permission(req1, None) is True

    req2 = rf.get("/api/v1/system_admin/roles/definitions/?category=office")
    assert perm.has_permission(req2, None) is True

    req3 = rf.get("/api/v1/system_admin/audit/?action=user_create")
    assert perm.has_permission(req3, None) is True
