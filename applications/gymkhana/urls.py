"""Gymkhana URL configuration — all viewsets via DefaultRouter."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClubBudgetRequestViewSet,
    ClubEventReportViewSet,
    ClubEventViewSet,
    ClubMembershipViewSet,
    ClubSessionViewSet,
    ClubViewSet,
    GymkhanaWorkflowHistoryViewSet,
    VenueViewSet,
    VotingPollViewSet,
)

router = DefaultRouter()
router.register(r'venues', VenueViewSet, basename='gymkhana-venue')
router.register(r'clubs', ClubViewSet, basename='gymkhana-club')
router.register(r'memberships', ClubMembershipViewSet, basename='gymkhana-membership')
router.register(r'sessions', ClubSessionViewSet, basename='gymkhana-session')
router.register(r'events', ClubEventViewSet, basename='gymkhana-event')
router.register(r'polls', VotingPollViewSet, basename='gymkhana-poll')
router.register(r'budget-requests', ClubBudgetRequestViewSet, basename='gymkhana-budget')
router.register(r'event-reports', ClubEventReportViewSet, basename='gymkhana-report')
router.register(r'workflow-history', GymkhanaWorkflowHistoryViewSet, basename='gymkhana-history')

urlpatterns = [
    path('', include(router.urls)),
]
