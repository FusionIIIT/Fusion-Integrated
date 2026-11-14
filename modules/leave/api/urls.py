from rest_framework.routers import DefaultRouter

from .views import LeaveBalanceViewSet, LeaveRequestViewSet

router = DefaultRouter()
router.register(r'balances', LeaveBalanceViewSet, basename='balance')
router.register(r'requests', LeaveRequestViewSet, basename='request')

urlpatterns = router.urls
