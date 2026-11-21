"""Verification tests for BR-SA-028: Denial of Self-Modification.

Traceability: CFR-SA-020, AFR-SA-075, BR-SA-028.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from modules.system_admin.api import permissions, views
from modules.system_admin.models import BasicUser


def test_super_admin_cannot_deactivate_self_via_permission(rf, super_admin_principal):
    """BR-SA-028: Super Admin cannot self-deactivate."""
    perm = permissions.DenySelfModification()
    view = MagicMock()
    view.kwargs = {"pk": str(super_admin_principal.user_id)}

    req = rf.post(f"/api/v1/system_admin/users/{super_admin_principal.user_id}/deactivate/")
    req.principal = super_admin_principal

    with pytest.raises(PermissionDenied, match="cannot self-modify their own account or status"):
        perm.has_permission(req, view)


def test_super_admin_cannot_deactivate_self_via_viewset(rf, super_admin_principal):
    """BR-SA-028: Viewset level rejection of self-deactivation."""
    view = views.UserViewSet.as_view({"post": "deactivate"})
    req = rf.post(
        f"/api/v1/system_admin/users/{super_admin_principal.user_id}/deactivate/",
        data={"reason": "Self-deactivation attempt"},
        format="json",
    )
    req.principal = super_admin_principal

    with patch("modules.system_admin.selectors.users.get_user_by_id") as mock_get_user:
        target = MagicMock(spec=BasicUser)
        target.id = super_admin_principal.user_id
        mock_get_user.return_value = target

        resp = view(req, pk=str(super_admin_principal.user_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_super_admin_cannot_update_own_profile_via_viewset(rf, super_admin_principal):
    """BR-SA-028: Viewset level rejection of self profile update."""
    view = views.UserViewSet.as_view({"patch": "partial_update"})
    req = rf.patch(
        f"/api/v1/system_admin/users/{super_admin_principal.user_id}/",
        data={"display_name": "New Admin Name"},
        format="json",
    )
    req.principal = super_admin_principal

    with patch("modules.system_admin.selectors.users.get_user_by_id") as mock_get_user:
        target = MagicMock(spec=BasicUser)
        target.id = super_admin_principal.user_id
        mock_get_user.return_value = target

        resp = view(req, pk=str(super_admin_principal.user_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_super_admin_can_modify_other_user(rf, super_admin_principal):
    """Permits modifying another user whose ID != principal.user_id."""
    perm = permissions.DenySelfModification()
    view = MagicMock()
    view.kwargs = {"pk": "99"}

    req = rf.post("/api/v1/system_admin/users/99/deactivate/")
    req.principal = super_admin_principal

    assert perm.has_permission(req, view) is True

    other_user = MagicMock(spec=BasicUser)
    other_user.id = 99
    assert perm.has_object_permission(req, view, other_user) is True
