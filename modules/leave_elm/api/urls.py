
from django.urls import path
from .views import ApplicationListView, BalanceListView, TaskListView, ApplicationActionView
from .configuration import ConfigurationView, RecordListView

urlpatterns = [
    path('applications', ApplicationListView.as_view(), name='application-list'),
    path('balances', BalanceListView.as_view(), name='balance-list'),
    path('tasks', TaskListView.as_view(), name='task-list'),
    path('applications/<int:pk>/action', ApplicationActionView.as_view(), name='application-action'),
    path('configuration', ConfigurationView.as_view(), name='configuration-view'),
    path('records', RecordListView.as_view(), name='record-list'),
]
