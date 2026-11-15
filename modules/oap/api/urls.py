from django.urls import path

from modules.oap.api import views

urlpatterns = [
    # Leave Management (OA-UC-01, 03, 04)
    path("leaves/", views.StudentLeaveListCreateView.as_view(), name="oap-leave-list-create"),
    path("leaves/<int:leave_id>/", views.StudentLeaveDetailView.as_view(), name="oap-leave-detail"),
    path("leaves/department/", views.DepartmentLeaveListView.as_view(), name="oap-leave-dept-list"),
    path("leaves/<int:leave_id>/decision/", views.HoDLeaveDecisionView.as_view(), name="oap-leave-decision"),

    # Bonafide Certificate (OA-UC-11, 12, 13, 14)
    path("bonafide/", views.StudentBonafideListCreateView.as_view(), name="oap-bonafide-list-create"),
    path("bonafide/all/", views.AcademicAdminBonafideListView.as_view(), name="oap-bonafide-admin-list"),
    path("bonafide/<int:request_id>/decision/", views.AcademicAdminBonafideDecisionView.as_view(), name="oap-bonafide-decision"),
    path("bonafide/<int:request_id>/download/", views.StudentBonafideDownloadView.as_view(), name="oap-bonafide-download"),

    # No-Dues Clearance (OA-UC-21, 22, 23, 24, 25)
    path("nodues/", views.StudentNoDuesListInitiateView.as_view(), name="oap-nodues-list-initiate"),
    path("nodues/<int:request_id>/", views.NoDuesDetailView.as_view(), name="oap-nodues-detail"),
    path("nodues/all/", views.AcademicAdminNoDuesListView.as_view(), name="oap-nodues-admin-list"),
    path("nodues/clearances/", views.AuthorityClearanceListView.as_view(), name="oap-nodues-authority-list"),
    path("nodues/<int:request_id>/verify/", views.AuthorityClearanceVerifyView.as_view(), name="oap-nodues-verify"),
    path("nodues/<int:request_id>/finalize/", views.AcademicAdminNoDuesFinalizeView.as_view(), name="oap-nodues-finalize"),
    path("nodues/<int:request_id>/download/", views.StudentNoDuesDownloadView.as_view(), name="oap-nodues-download"),

    # Assignments (OA-UC-41, 42)
    path("assignments/thesis/", views.ThesisAssignmentListCreateView.as_view(), name="oap-assignment-thesis"),
    path("assignments/ta/", views.TAAssignmentListCreateView.as_view(), name="oap-assignment-ta"),

    # Assistantship Claim (OA-UC-31, 33, 34, 35, 36, 37)
    path("assistantship/claims/", views.StudentAssistantshipClaimListCreateView.as_view(), name="oap-assistantship-list-create"),
    path("assistantship/claims/<int:claim_id>/", views.AssistantshipClaimDetailView.as_view(), name="oap-assistantship-detail"),
    path("assistantship/supervisor-queue/", views.SupervisorClaimListView.as_view(), name="oap-assistantship-supervisor-queue"),
    path("assistantship/claims/<int:claim_id>/verify/", views.SupervisorClaimVerifyView.as_view(), name="oap-assistantship-verify"),
    path("assistantship/dept-queue/", views.DepartmentAdminClaimReviewListView.as_view(), name="oap-assistantship-dept-queue"),
    path("assistantship/claims/<int:claim_id>/forward/", views.DepartmentAdminClaimForwardView.as_view(), name="oap-assistantship-forward"),
    path("assistantship/hod-queue/", views.HoDClaimListView.as_view(), name="oap-assistantship-hod-queue"),
    path("assistantship/claims/<int:claim_id>/decision/", views.HoDClaimDecisionView.as_view(), name="oap-assistantship-decision"),
    path("assistantship/disbursement-queue/", views.AcademicAdminDisbursementListView.as_view(), name="oap-assistantship-disburse-queue"),
    path("assistantship/claims/<int:claim_id>/disburse/", views.AcademicAdminDisburseView.as_view(), name="oap-assistantship-disburse"),

    # Graduate Seminar (OA-UC-51, 53, 54)
    path("seminars/requests/", views.StudentSeminarRequestListCreateView.as_view(), name="oap-seminar-request-list-create"),
    path("seminars/admin-queue/", views.DepartmentAdminSeminarListView.as_view(), name="oap-seminar-admin-queue"),
    path("seminars/<int:seminar_id>/schedule/", views.DepartmentAdminSeminarScheduleView.as_view(), name="oap-seminar-schedule"),
    path("seminars/schedules/", views.PublicSeminarScheduleListView.as_view(), name="oap-seminar-schedules"),

    # Notifications (OA-UC-91, 92)
    path("notifications/", views.OAPNotificationListView.as_view(), name="oap-notifications-list"),
    path("notifications/<int:notification_id>/read/", views.OAPNotificationMarkReadView.as_view(), name="oap-notifications-read"),
]
