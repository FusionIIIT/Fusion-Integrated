from rest_framework.routers import DefaultRouter
from .views import LeaveRequestList, LeaveRequestDetail, LeaveApprovalList, LeaveApprovalDetail

router = DefaultRouter()
router.register(r'leave-requests', LeaveRequestList)
router.register(r'leave-approvals', LeaveApprovalList)

urlpatterns = router.urls