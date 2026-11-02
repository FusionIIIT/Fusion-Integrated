from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"expenses", views.ExpenseRequestViewSet, basename="iaa-expense")
router.register(r"ta-claims", views.TravelAllowanceClaimViewSet, basename="iaa-ta")
router.register(r"budgets", views.DepartmentBudgetViewSet, basename="iaa-budget")
router.register(r"anomalies", views.AnomalyRecordViewSet, basename="iaa-anomaly")
router.register(r"audit-observations", views.AuditObservationViewSet, basename="iaa-audit")
router.register(r"actions", views.ApprovalActionViewSet, basename="iaa-action")

urlpatterns = router.urls
