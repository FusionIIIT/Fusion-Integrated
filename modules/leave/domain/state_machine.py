"""Authoritative State-Transition Tables for Employee Leave Management.

Implements all 17 Basis Workflows (BW-EL-01..17) and 4 Composite Workflows
(CW-EL-01..04) from Workflow Specifications v1.6.
"""
from __future__ import annotations


# Authoritative states matching Workflow Specifications v1.6
class LeaveState:
    DRAFT = "draft"
    AWAITING_SUBSTITUTE = "awaiting_substitute"
    APPLICANT_ACTION_REQUIRED = "applicant_action_required"
    AWAITING_UNIT_HEAD = "awaiting_unit_head"
    AWAITING_ESTABLISHMENT = "awaiting_establishment"
    AWAITING_SANCTION = "awaiting_sanction"
    AWAITING_DIRECTOR = "awaiting_director"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    # Cancellation states (CW-EL-02)
    CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
    CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
    CANCELLATION_PENDING_SANCTION = "cancellation_pending_sanction"
    CANCELLED = "cancelled"

    # Extension states (CW-EL-03)
    AWAITING_EXTENSION_SUBSTITUTE = "awaiting_extension_substitute"
    EXTENSION_APPLICANT_ACTION_REQUIRED = "extension_applicant_action_required"
    AWAITING_EXTENSION_UNIT_HEAD = "awaiting_extension_unit_head"
    EXTENSION_PENDING_ESTABLISHMENT = "extension_pending_establishment"
    EXTENSION_PENDING_SANCTION = "extension_pending_sanction"
    EXTENDED = "extended"

    # Resumption states (CW-EL-04)
    RESUMPTION_REVIEW_PENDING = "resumption_review_pending"
    RESUMPTION_NO_ADJUSTMENT = "resumption_reviewed_no_adjustment"
    RESUMPTION_EARLY_SYNCHRONIZED = "resumption_reviewed_early_synchronized"
    RESUMPTION_LATE_SYNCHRONIZED = "resumption_reviewed_late_synchronized"


# Permissions governing transitions across workflows
WORKFLOW_PERMISSIONS = {
    "apply": "leave.request.create",
    "withdraw": "leave.request.delete",
    "respond_substitute": "leave.request.view_self",
    "review_unit_head": "leave.request.approve",
    "route_establishment": "leave.request.approve",
    "sanction": "leave.request.approve",
    "resumption_review": "leave.request.approve",
    "record_offline": "leave.balance.update",
    "admin_config": "leave.type.manage",
}
