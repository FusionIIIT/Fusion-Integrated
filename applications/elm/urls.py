from django.urls import path
from .views import ApplyLeaveView, WithdrawLeaveView, ReviewLeaveView

urlpatterns = [
    path('apply/', ApplyLeaveView.as_view(), name='elm-apply'),
    path('withdraw/<int:pk>/', WithdrawLeaveView.as_view(), name='elm-withdraw'),
    path('review/<int:pk>/', ReviewLeaveView.as_view(), name='review_leave'),   
]