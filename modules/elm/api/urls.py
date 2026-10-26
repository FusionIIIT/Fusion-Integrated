from django.urls import path

from modules.elm.api.views import (
    LeaveApplicationListView,
    LeaveBalanceListView,
    LeaveTypeListView,
    SubstituteNomineeListView,
)

urlpatterns = [
    path('leave-types/', LeaveTypeListView.as_view(), name='leave-type-list'),
    path('leave-balances/', LeaveBalanceListView.as_view(), name='leave-balance-list'),
    path('leave-applications/', LeaveApplicationListView.as_view(), name='leave-application-list'),
    path(
        'substitute-nominees/',
        SubstituteNomineeListView.as_view(),
        name='substitute-nominee-list'
    ),
]
