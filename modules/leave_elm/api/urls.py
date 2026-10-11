from rest_framework.routers import DefaultRouter
from django.urls import path, include
from modules.leave_elm.api.views import (
    LeaveApplicationViewSet, 
    LeaveBalanceViewSet, 
    SubstituteResponseViewSet
)

# Initialize the router and register views
router = DefaultRouter()
router.register(r'applications', LeaveApplicationViewSet, basename='leave-application')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'substitutes', SubstituteResponseViewSet, basename='substitute-response')


urlpatterns = [
    # API endpoints for ELM module
    path('', include(router.urls)),
]