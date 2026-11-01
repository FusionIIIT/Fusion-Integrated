from django.urls import path
from .views import ApplyLeaveView, WithdrawLeaveView

urlpatterns = [
    path('apply/', ApplyLeaveView.as_view(), name='elm-apply'),
    path('withdraw/<int:pk>/', WithdrawLeaveView.as_view(), name='elm-withdraw'),
]