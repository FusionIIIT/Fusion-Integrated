"""DRF permission helpers for the IWD module."""

from fusion_auth.permissions import HasModuleGrant, HasPermission

RequireIwdModule = HasModuleGrant("iwd")
RequireComplaintCreate = HasPermission("iwd.complaint.create")
RequireComplaintView = HasPermission("iwd.complaint.view")
RequireComplaintUpdate = HasPermission("iwd.complaint.update")
RequireEstimateCreate = HasPermission("iwd.estimate.create")
RequireEstimateReview = HasPermission("iwd.estimate.review")
RequireInventoryManage = HasPermission("iwd.inventory.manage")
RequireWorkVerify = HasPermission("iwd.work.verify")
RequireBillCreate = HasPermission("iwd.bill.create")
RequireBillReview = HasPermission("iwd.bill.review")
RequireFeedbackCreate = HasPermission("iwd.feedback.create")
RequireFeedbackView = HasPermission("iwd.feedback.view")
