"""URL routing for Mess Management System (MMS) API."""
from django.urls import path

from modules.mms.api import views

app_name = "mms"

urlpatterns = [
    # Role management (Mess Admin)
    path("roles/", views.RoleAssignmentView.as_view(), name="roles"),
    path("roles/active/", views.ActiveRolesView.as_view(), name="roles-active"),

    # Registration windows
    path("window/", views.RegistrationWindowView.as_view(), name="window"),

    # Student registration & deregistration
    path("registration/mine/", views.StudentRegistrationView.as_view(), name="registration-mine"),
    path(
        "registration/submit/",
        views.StudentRegistrationView.as_view(),
        name="registration-submit",
    ),
    path(
        "registration/<int:registration_id>/deregister/",
        views.StudentDeregistrationView.as_view(),
        name="registration-deregister",
    ),

    # Caretaker registration reviews
    path("registrations/", views.RegistrationsListView.as_view(), name="registrations-list"),
    path(
        "registrations/<int:registration_id>/review/",
        views.ReviewRegistrationView.as_view(),
        name="registration-review",
    ),
    path(
        "registrations/<int:registration_id>/review-deregister/",
        views.ReviewDeregistrationView.as_view(),
        name="deregistration-review",
    ),

    # Weekly menu
    path("menu/", views.WeeklyMenuView.as_view(), name="menu"),

    # Rebates
    path("rebates/mine/", views.StudentRebatesView.as_view(), name="rebates-mine"),
    path("rebates/apply/", views.StudentRebatesView.as_view(), name="rebates-apply"),
    path("rebates/", views.RebatesListView.as_view(), name="rebates-list"),
    path("rebates/<int:rebate_id>/review/", views.ReviewRebateView.as_view(), name="rebate-review"),

    # Feedback
    path("feedback/", views.FeedbackView.as_view(), name="feedback"),
]
