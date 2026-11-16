"""DRF permissions for Leave Management endpoints."""
from __future__ import annotations

from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE = HasModuleGrant("leave")

P_VIEW_SELF = "leave.request.view_self"
P_CREATE = "leave.request.create"
P_DELETE = "leave.request.delete"
P_VIEW = "leave.request.view"
P_APPROVE = "leave.request.approve"
P_BALANCE_UPDATE = "leave.balance.update"
P_TYPE_MANAGE = "leave.type.manage"

MayViewSelf = HasPermission(P_VIEW_SELF)
MayCreateRequest = HasPermission(P_CREATE)
MayCancelRequest = HasPermission(P_DELETE)
MayApproveRequest = HasPermission(P_APPROVE)
MayViewRequests = HasPermission(P_VIEW)
MayUpdateBalance = HasPermission(P_BALANCE_UPDATE)

