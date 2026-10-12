from django.urls import path, include
from rest_framework.routers import DefaultRouter
from modules.elm import views

router = DefaultRouter()
router.register(r'leave-types', views.LeaveTypeViewSet)
router.register(r'leave-balances', views.LeaveBalanceViewSet)
router.register(r'leave-applications', views.LeaveApplicationViewSet)
router.register(r'leave-substitutes', views.LeaveSubstituteViewSet)
router.register(r'leave-approvals', views.LeaveApprovalViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
