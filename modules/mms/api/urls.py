"""MMS API URL routing."""

from django.urls import path

from modules.mms.api import views

app_name = "mms"

urlpatterns = [
    # Special Food
    path(
        "special-food-requests/",
        views.SpecialFoodRequestListCreateView.as_view(),
        name="special-food-list",
    ),
    path(
        "special-food-requests/<int:pk>/",
        views.SpecialFoodRequestDetailView.as_view(),
        name="special-food-detail",
    ),
    path(
        "special-food-requests/<int:pk>/decision/",
        views.SpecialFoodDecisionView.as_view(),
        name="special-food-decision",
    ),
    path(
        "special-food-requests/<int:pk>/fulfill/",
        views.SpecialFoodFulfillView.as_view(),
        name="special-food-fulfill",
    ),
    # Registration
    path(
        "registration-requests/",
        views.RegistrationListCreateView.as_view(),
        name="registration-list",
    ),
    path(
        "registration-requests/<int:pk>/",
        views.RegistrationDetailView.as_view(),
        name="registration-detail",
    ),
    path(
        "registration-requests/<int:pk>/decision/",
        views.RegistrationDecisionView.as_view(),
        name="registration-decision",
    ),
    path(
        "registration-window/", views.RegistrationWindowView.as_view(), name="registration-window"
    ),
    # Deregistration
    path(
        "deregistration-requests/",
        views.DeregistrationListCreateView.as_view(),
        name="deregistration-list",
    ),
    path(
        "deregistration-requests/<int:pk>/",
        views.DeregistrationDetailView.as_view(),
        name="deregistration-detail",
    ),
    path(
        "deregistration-requests/<int:pk>/decision/",
        views.DeregistrationDecisionView.as_view(),
        name="deregistration-decision",
    ),
    # Rebate
    path("rebate-requests/", views.RebateRequestListCreateView.as_view(), name="rebate-list"),
    path(
        "rebate-requests/<int:pk>/", views.RebateRequestDetailView.as_view(), name="rebate-detail"
    ),
    path(
        "rebate-requests/<int:pk>/decision/",
        views.RebateDecisionView.as_view(),
        name="rebate-decision",
    ),
    # Menu
    path("menu/", views.MenuListView.as_view(), name="menu-list"),
    path("menu/items/", views.MenuItemManageView.as_view(), name="menu-item-manage"),
    # Billing
    path("bills/", views.MonthlyBillListView.as_view(), name="bill-list"),
    path("bills/<int:pk>/", views.MonthlyBillDetailView.as_view(), name="bill-detail"),
    path("bills/generate/", views.MonthlyBillGenerateView.as_view(), name="bill-generate"),
    path("bills/<int:pk>/finalize/", views.MonthlyBillFinalizeView.as_view(), name="bill-finalize"),
    path("bills/<int:pk>/publish/", views.MonthlyBillPublishView.as_view(), name="bill-publish"),
    # Feedback
    path("feedback/", views.FeedbackListCreateView.as_view(), name="feedback-list"),
    # Vacation Surveys
    path("surveys/", views.VacationSurveyListCreateView.as_view(), name="survey-list"),
    path(
        "surveys/<int:survey_id>/respond/",
        views.VacationResponseCreateView.as_view(),
        name="survey-respond",
    ),
    path("survey-summary/", views.VacationSurveySummaryView.as_view(), name="survey-summary"),
    # Announcements
    path("announcements/", views.AnnouncementListCreateView.as_view(), name="announcement-list"),
    path(
        "announcements/history/",
        views.AnnouncementHistoryView.as_view(),
        name="announcement-history",
    ),
    # Reports
    path("reports/operational/", views.OperationalReportView.as_view(), name="report-operational"),
    path("reports/supervisory/", views.SupervisoryReportView.as_view(), name="report-supervisory"),
    # Roles
    path("roles/", views.RoleAssignmentListCreateView.as_view(), name="role-list"),
    # Unified requests overview
    path("requests/", views.StudentRequestsOverviewView.as_view(), name="requests-overview"),
]
