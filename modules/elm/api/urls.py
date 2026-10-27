"""URL routing for Employee Leave Management API."""
from rest_framework.routers import DefaultRouter

from .views import (
    AdminOperationsViewSet,
    ApprovalQueueViewSet,
    BalanceViewSet,
    LeaveRequestViewSet,
    SubstituteViewSet,
)

router = DefaultRouter()
router.register(r"requests", LeaveRequestViewSet, basename="elm-requests")
router.register(r"substitute", SubstituteViewSet, basename="elm-substitute")
router.register(r"approvals", ApprovalQueueViewSet, basename="elm-approvals")
router.register(r"balances", BalanceViewSet, basename="elm-balances")
router.register(r"admin", AdminOperationsViewSet, basename="elm-admin")

urlpatterns = router.urls
