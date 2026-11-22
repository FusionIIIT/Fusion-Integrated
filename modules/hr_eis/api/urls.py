from django.urls import path, include
from rest_framework.routers import DefaultRouter
from modules.hr_eis.api.views import (
    EmployeeProfileViewSet, LeaveBalanceViewSet, LeaveRequestViewSet,
    AppraisalRecordViewSet, LtcClaimViewSet, CpdaClaimViewSet,
    AuditLogViewSet, NotificationViewSet, WorkflowSettingViewSet
)

router = DefaultRouter()
router.register("profiles", EmployeeProfileViewSet, basename="eis-profiles")
router.register("balances", LeaveBalanceViewSet, basename="eis-balances")
router.register("leaves", LeaveRequestViewSet, basename="eis-leaves")
router.register("appraisals", AppraisalRecordViewSet, basename="eis-appraisals")
router.register("ltc", LtcClaimViewSet, basename="eis-ltc")
router.register("cpda", CpdaClaimViewSet, basename="eis-cpda")
router.register("audit", AuditLogViewSet, basename="eis-audit")
router.register("notifications", NotificationViewSet, basename="eis-notifications")
router.register("settings", WorkflowSettingViewSet, basename="eis-settings")

urlpatterns = [
    path("", include(router.urls)),
]
