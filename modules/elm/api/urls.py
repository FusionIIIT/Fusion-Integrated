from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("balances", views.BalanceListView.as_view()),
    path("categories", views.CategoryListView.as_view()),
    path("applications", views.ApplicationListCreateView.as_view()),
    path("applications/<int:pk>/withdraw", views.ApplicationWithdrawView.as_view()),
    path("calendar", views.HolidayListView.as_view()),
]
