from django.urls import path
from .views import LeaveBalanceViewSet, LeaveRequestViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'balances', LeaveBalanceViewSet, basename='balance')
router.register(r'requests', LeaveRequestViewSet, basename='request')

urlpatterns = router.urls
