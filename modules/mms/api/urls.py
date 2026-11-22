from django.urls import path

from modules.mms.api import views

app_name = "mms"

urlpatterns = [
    path("roles/", views.RoleAssignmentsView.as_view(), name="roles"),
    path(
        "registration-windows/",
        views.RegistrationWindowsView.as_view(),
        name="registration-windows",
    ),
    path("registrations/", views.RegistrationsView.as_view(), name="registrations"),
    path(
        "registrations/<int:request_id>/decision/",
        views.RegistrationDecisionView.as_view(),
        name="registration-decision",
    ),
    path("menu/", views.MenuView.as_view(), name="menu"),
    path("rebates/", views.RebateView.as_view(), name="rebates"),
    path(
        "rebates/<int:request_id>/decision/",
        views.RebateDecisionView.as_view(),
        name="rebate-decision",
    ),
    path("vacation-surveys/", views.VacationSurveysView.as_view(), name="vacation-surveys"),
    path(
        "vacation-surveys/<int:survey_id>/response/",
        views.VacationResponseView.as_view(),
        name="vacation-response",
    ),
    path("special-food/", views.SpecialFoodView.as_view(), name="special-food"),
    path(
        "special-food/<int:request_id>/decision/",
        views.SpecialFoodDecisionView.as_view(),
        name="special-food-decision",
    ),
    path(
        "special-food/<int:request_id>/fulfillment/",
        views.SpecialFoodFulfillmentView.as_view(),
        name="special-food-fulfillment",
    ),
    path("feedback/", views.FeedbackView.as_view(), name="feedback"),
    path("announcements/", views.AnnouncementsView.as_view(), name="announcements"),
    path("reports/", views.ReportsView.as_view(), name="reports"),
]
