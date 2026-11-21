from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ApplicationListView, ApplicationDetailView, ApplicationHistoryView,
    SubmitApplicationView, AssignDirectorView, ReviewApplicationView,
    ResubmitApplicationView, WithdrawApplicationView, FileAppealView,
    DecideAppealView, ExpireOverdueResubmissionsView, AdminApplicationListView
)
from .views_legal import (
    AssignAttorneyView, RespondToAssignmentView, MyAttorneyAssignmentsView,
    RecordOpinionView, ProposeBudgetView, DecideBudgetView, RecordFilingView,
    RecordOfficeActionView, PrepareResponseView, ApproveResponseView, SubmitResponseView,
    RecordGrantView, ScheduleMaintenanceView, DecideRenewalView
)

router = DefaultRouter()

# --- Application Routes ---
router.register(r'applications', ApplicationListView, basename='application-list')
router.register(r'applications/(?P<pk>[0-9]+)/', ApplicationDetailView, basename='application-detail')
router.register(r'history/', ApplicationHistoryView, basename='application-history')

# --- Action Routes ---
router.register(r'submit/', SubmitApplicationView, basename='submit-application')
router.register(r'assign-director/', AssignDirectorView, basename='assign-director')
router.register(r'review/', ReviewApplicationView, basename='review-application')
router.register(r'resubmit/', ResubmitApplicationView, basename='resubmit-application')
router.register(r'withdraw/', WithdrawApplicationView, basename='withdraw-application')
router.register(r'appeal/', FileAppealView, basename='file-appeal')
router.register(r'appeals/(?P<pk>[0-9]+)/', DecideAppealView, basename='decide-appeal')

# --- Admin Routes ---
router.register(r'', ExpireOverdueResubmissionsView, basename='admin-expire-resubmissions')
router.register(r'applications/', AdminApplicationListView, basename='admin-application-list')

# --- Legal Service Routes ---
router.register(r'assign-attorney/', AssignAttorneyView, basename='assign-attorney')
router.register(r'assignments/(?P<pk>[0-9]+)/', RespondToAssignmentView, basename='respond-to-assignment')
router.register(r'my-assignments/', MyAttorneyAssignmentsView, basename='my-attorney-assignments')
router.register(r'opinions/(?P<pk>[0-9]+)/', RecordOpinionView, basename='record-opinion')
router.register(r'budgets/(?P<pk>[0-9]+)/', ProposeBudgetView, basename='propose-budget')
router.register(r'budgets/(?P<pk>[0-9]+)/decide/', DecideBudgetView, basename='decide-budget')
router.register(r'filings/(?P<pk>[0-9]+)/', RecordFilingView, basename='record-filing')
router.register(r'office-actions/(?P<pk>[0-9]+)/', RecordOfficeActionView, basename='record-office-action')
router.register(r'office-actions/(?P<pk>[0-9]+)/response/', PrepareResponseView, basename='prepare-response')
router.register(r'office-actions/(?P<pk>[0-9]+)/response/approve/', ApproveResponseView, basename='approve-response')
router.register(r'office-actions/(?P<pk>[0-9]+)/response/submit/', SubmitResponseView, basename='submit-response')
router.register(r'applications/(?P<pk>[0-9]+)/grant/', RecordGrantView, basename='record-grant')
router.register(r'maintenance/(?P<pk>[0-9]+)/', ScheduleMaintenanceView, basename='schedule-maintenance')
router.register(r'maintenance/(?P<pk>[0-9]+)/decide/', DecideRenewalView, basename='decide-renewal')

urlpatterns = [
    path('', include(router.urls)),
]
