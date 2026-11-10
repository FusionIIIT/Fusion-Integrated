from django.urls import path
from .views import (
    RegistrationView, DeregistrationView, RebateView, SpecialFoodView,
    VacationSurveyResponseView, FeedbackView, StudentBillView,
    CaretakerReviewView, BillingManagementView, AnnouncementView,
    MenuView, ReportsView
)

urlpatterns = [
    # Student Action Endpoints
    path('register/', RegistrationView.as_view()),
    path('deregister/', DeregistrationView.as_view()),
    path('rebate/', RebateView.as_view()),
    path('special-food/', SpecialFoodView.as_view()),
    path('survey/<int:survey_id>/respond/', VacationSurveyResponseView.as_view()),
    path('feedback/', FeedbackView.as_view()),
    path('my-bills/', StudentBillView.as_view()),
    path('menu/', MenuView.as_view()),
    path('announcements/', AnnouncementView.as_view()),

    # Operational Caretaker Review & Billing Action Endpoints
    path('review/<str:module_type>/<int:pk>/', CaretakerReviewView.as_view()),
    path('billing/', BillingManagementView.as_view()),
    path('billing/<int:bill_id>/publish/', BillingManagementView.as_view()),

    # Supervisory & Operational Reports
    path('reports/<str:report_type>/', ReportsView.as_view()),
]