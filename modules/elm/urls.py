from django.urls import path
from .views import apply_for_leave_view, approve_leave_view, reject_leave_view

urlpatterns = [
    path('apply-for-leave/', apply_for_leave_view, name='apply-for-leave'),
    path('approve-leave/', approve_leave_view, name='approve-leave'),
    path('reject-leave/', reject_leave_view, name='reject-leave'),
]