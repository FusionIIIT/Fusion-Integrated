"""Permission code constants for the IWD module (ADR-0010, BR-IWD-001).

Derived from authoritative requirements:
- CFR-IWD-01..16
- AFR-IWD-001..060
- BR-IWD-001, BR-IWD-018
- Use cases UC-IWD-001..151
"""

MODULE_CODE = "iwd"

# Complainant actions (AFR-IWD-001, AFR-IWD-008, AFR-IWD-046..048)
COMPLAINT_CREATE = "iwd.complaint.create"
COMPLAINT_VIEW_SELF = "iwd.complaint.view_self"
COMPLAINT_VIEW = "iwd.complaint.view"
FEEDBACK_CREATE = "iwd.feedback.create"
FEEDBACK_VIEW = "iwd.feedback.view"

# Engineer actions (AFR-IWD-010..013, AFR-IWD-032..033, AFR-IWD-040)
COMPLAINT_ASSESS = "iwd.complaint.assess"
WORK_EXECUTE = "iwd.work.execute"
BILL_CREATE = "iwd.bill.create"
URGENT_FLAG = "iwd.urgent.flag"

# IWD Admin actions (AFR-IWD-016, AFR-IWD-023, AFR-IWD-027..031)
ESTIMATE_REVIEW_LOW = "iwd.estimate.review_low"
INVENTORY_MANAGE = "iwd.inventory.manage"
BIDDING_MANAGE = "iwd.bidding.manage"

# Review Committee & Department Head actions (AFR-IWD-019..020, AFR-IWD-034, AFR-IWD-039)
ESTIMATE_REVIEW_COMMITTEE = "iwd.estimate.review_committee"
ESTIMATE_REVIEW_MID = "iwd.estimate.review_mid"
WORK_VERIFY = "iwd.work.verify"
URGENT_REVIEW = "iwd.urgent.review"

# Director actions (AFR-IWD-021..022, AFR-IWD-044)
ESTIMATE_REVIEW_DIRECTOR = "iwd.estimate.review_director"
PAYMENT_APPROVE = "iwd.payment.approve"

# Auditor & Accounts actions (AFR-IWD-041..043, AFR-IWD-045)
BILL_AUDIT = "iwd.bill.audit"
PAYMENT_SETTLE = "iwd.payment.settle"

# System operations (AFR-IWD-007, BR-IWD-002)
COMPLAINT_AUTO_ASSIGN = "iwd.complaint.auto_assign"

