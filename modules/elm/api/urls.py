from django.urls import path
from . import views as v
urlpatterns=[
 path("leaves",v.LeaveListCreateView.as_view()),
 path("leaves/<int:pk>/submit",v.LeaveSubmitView.as_view()),
 path("leaves/<int:pk>/withdraw",v.LeaveWithdrawView.as_view()),
 path("leaves/balances",v.BalancesView.as_view()),
 path("reviews",v.ReviewListView.as_view()),
 path("reviews/<int:pk>",v.ReviewActionView.as_view()),
 path("admin/policies",v.PolicyView.as_view()),
 path("admin/policies/<int:pk>",v.PolicyView.as_view()),
 path("admin/holidays",v.HolidayView.as_view()),
 path("admin/sla",v.SlaView.as_view()),
]
