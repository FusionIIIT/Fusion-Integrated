from rest_framework.routers import DefaultRouter

from modules.hreis.views import (
    AuditEventViewSet,
    EmployeeRecordViewSet,
    HRRequestViewSet,
    LeaveAccountViewSet,
    LeavePolicyViewSet,
    NotificationViewSet,
    WorkflowRouteViewSet,
)

router = DefaultRouter()
router.register(r"employees", EmployeeRecordViewSet, basename="hreis-employees")
router.register(r"policies", LeavePolicyViewSet, basename="hreis-policies")
router.register(r"accounts", LeaveAccountViewSet, basename="hreis-accounts")
router.register(r"routes", WorkflowRouteViewSet, basename="hreis-routes")
router.register(r"requests", HRRequestViewSet, basename="hreis-requests")
router.register(r"audit", AuditEventViewSet, basename="hreis-audit")
router.register(r"notifications", NotificationViewSet, basename="hreis-notifications")

urlpatterns = router.urls
