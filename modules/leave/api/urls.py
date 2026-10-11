from django.urls import path
from .views import (
    LeaveRequestListCreateView,
    LeaveBalanceView,
    LeaveApprovalView,
)

app_name = 'leave'

urlpatterns = [
    path('requests/', LeaveRequestListCreateView.as_view(), name='request_list'),
    path('requests/<int:pk>/', LeaveRequestListCreateView.as_view(), name='request_detail'),
    path('balances/', LeaveBalanceView.as_view(), name='balance_list'),
    path('approve/<int:request_id>/', LeaveApprovalView.as_view(), name='approve_request'),
    path('reject/<int:request_id>/', LeaveApprovalView.as_view(), name='reject_request'),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaveRequestListCreateView, LeaveBalanceView, LeaveApprovalView

app_name = 'leave'

router = DefaultRouter()
router.register(r'requests', LeaveRequestListCreateView, basename='request')

urlpatterns = [
    path('', include(router.urls)),
    path('balances/', LeaveBalanceView.as_view(), name='balance_list'),
    path('approve/<int:request_id>/', LeaveApprovalView.as_view(), name='approve_request'),
    path('reject/<int:request_id>/', LeaveApprovalView.as_view(), name='reject_request'),
]
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import LeaveRequestListCreateView, LeaveBalanceView, LeaveApprovalView

app_name = 'leave'

router = DefaultRouter()
router.register(r'requests', LeaveRequestListCreateView, basename='request')

urlpatterns = [
    path('', include(router.urls)),
    path('balances/', LeaveBalanceView.as_view(), name='balance_list'),
    path('approve/<int:request_id>/', LeaveApprovalView.as_view(), name='approve_request'),
    path('reject/<int:request_id>/', LeaveApprovalView.as_view(), name='reject_request'),
]
