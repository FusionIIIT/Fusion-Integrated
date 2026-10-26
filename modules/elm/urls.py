# modules/elm/urls.py

from django.urls import path
from .views import apply_for_leave_view, approve_leave_request_view, reject_leave_request_view

urlpatterns = [
    path('apply_for_leave/', apply_for_leave_view),
    path('approve_leave_request/', approve_leave_request_view),
    path('reject_leave_request/', reject_leave_request_view),
]
