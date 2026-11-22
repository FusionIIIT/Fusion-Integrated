"""Authorization gates for Other Academic Procedures.

Enforces module-level grant and specific action-level permissions
using the institutional IAM principal (ADR-0010).
"""
from __future__ import annotations

from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE = HasModuleGrant("oap")

# Permission codes declared in registry.py
P_REQUEST_VIEW_SELF = "oap.request.view_self"
P_LEAVE_CREATE = "oap.leave.create"
P_LEAVE_VIEW_SELF = "oap.leave.view_self"
P_LEAVE_RECOMMEND = "oap.leave.recommend"
P_LEAVE_APPROVE = "oap.leave.approve"
P_BONAFIDE_CREATE = "oap.bonafide.create"
P_BONAFIDE_VIEW_SELF = "oap.bonafide.view_self"
P_BONAFIDE_ISSUE = "oap.bonafide.issue"
P_NODUES_VIEW = "oap.nodues.view"
P_NODUES_INITIATE = "oap.nodues.initiate"
P_NODUES_SIGNOFF = "oap.nodues.signoff"
P_NODUES_FINALIZE = "oap.nodues.finalize"
P_BRANCHCHANGE_APPLY = "oap.branchchange.apply"
P_BRANCHCHANGE_MANAGE = "oap.branchchange.manage"
P_BRANCHCHANGE_APPROVE = "oap.branchchange.approve"

__all__ = [
    "MODULE",
    "P_BONAFIDE_CREATE",
    "P_BONAFIDE_ISSUE",
    "P_BONAFIDE_VIEW_SELF",
    "P_BRANCHCHANGE_APPLY",
    "P_BRANCHCHANGE_APPROVE",
    "P_BRANCHCHANGE_MANAGE",
    "P_LEAVE_APPROVE",
    "P_LEAVE_CREATE",
    "P_LEAVE_RECOMMEND",
    "P_LEAVE_VIEW_SELF",
    "P_NODUES_FINALIZE",
    "P_NODUES_INITIATE",
    "P_NODUES_SIGNOFF",
    "P_NODUES_VIEW",
    "P_REQUEST_VIEW_SELF",
    "HasPermission",
]
