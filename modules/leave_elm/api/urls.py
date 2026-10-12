"""Leave Management API URLs."""
from django.urls import path
from .views import LeaveAPI

app_name = 'leave_elm'

urlpatterns = [
    path('', LeaveAPI.as_view({'get': 'mine'}), name='root'),
    path('mine', LeaveAPI.as_view({'get': 'mine'}), name='mine'),
    path('apply', LeaveAPI.as_view({'post': 'apply'}), name='apply'),
    path('<int:id>', LeaveAPI.as_view({'get': 'details'}), name='detail'),
    path('<int:id>/withdraw', LeaveAPI.as_view({'post': 'withdraw'}), name='withdraw'),
    path('<int:id>/cancel', LeaveAPI.as_view({'post': 'cancel'}), name='cancel'),
    path('<int:id>/extend', LeaveAPI.as_view({'post': 'extend'}), name='extend'),
    path('<int:id>/resumption', LeaveAPI.as_view({'post': 'resumption'}), name='resumption'),
    path('balances', LeaveAPI.as_view({'get': 'balances'}), name='balances'),
    path('history', LeaveAPI.as_view({'get': 'history'}), name='history'),
    path('queue', LeaveAPI.as_view({'get': 'queue'}), name='queue'),
    path('<int:id>/substitute/accept', LeaveAPI.as_view({'post': 'substitute_accept'}), name='substitute_accept'),
    path('<int:id>/substitute/decline', LeaveAPI.as_view({'post': 'substitute_decline'}), name='substitute_decline'),
    path('<int:id>/review', LeaveAPI.as_view({'post': 'review'}), name='review'),
    path('policy', LeaveAPI.as_view({'get': 'policy'}), name='policy'),
    path('calendar', LeaveAPI.as_view({'get': 'calendar'}), name='calendar'),
    path('offline-record', LeaveAPI.as_view({'post': 'offline_record'}), name='offline_record'),
    path('notifications', LeaveAPI.as_view({'get': 'notifications'}), name='notifications'),
]
