"""URL routing for MMS API."""

from django.urls import path
from modules.mms.api import views

urlpatterns = [
    path("menu/", views.MenuView.as_view(), name="mms-menu"),
    path("menu/manage/", views.ManageMenuView.as_view(), name="mms-manage-menu"),
    path("windows/", views.RegistrationWindowView.as_view(), name="mms-windows"),
    path("registrations/", views.RegistrationView.as_view(), name="mms-registrations"),
    path("registrations/<int:pk>/review/", views.ReviewRegistrationView.as_view(), name="mms-review-registration"),
    path("rebates/", views.RebateView.as_view(), name="mms-rebates"),
    path("rebates/review/", views.ReviewRebateView.as_view(), name="mms-review-rebates-list"),
    path("rebates/<int:pk>/review/", views.ReviewRebateView.as_view(), name="mms-review-rebate"),
    path("feedback/", views.FeedbackView.as_view(), name="mms-feedback"),
    path("roles/", views.AssignRoleView.as_view(), name="mms-roles"),
]
