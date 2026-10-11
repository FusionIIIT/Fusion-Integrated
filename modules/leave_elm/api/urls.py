from rest_framework.routers import DefaultRouter
from modules.leave_elm.api.views import LeaveTypeViewSet, LeaveBalanceViewSet, LeaveApplicationViewSet

router = DefaultRouter()
router.register(r'types', LeaveTypeViewSet, basename='leave-type')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'applications', LeaveApplicationViewSet, basename='leave-application')

urlpatterns = router.urls
