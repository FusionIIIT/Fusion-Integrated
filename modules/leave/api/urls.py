from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    # employee self-service endpoints
    path("me/requests", v.MyRequestsView.as_view(), name="leave-my-requests"),
    path("me/balances", v.MyBalancesView.as_view(), name="leave-my-balances"),
    path("me/statement/<str:category>", v.MyStatementView.as_view(), name="leave-my-statement"),
    path("requests", v.ApplyLeaveView.as_view(), name="leave-requests"),
    path("requests/<int:pk>", v.LeaveDetailView.as_view(), name="leave-request-detail"),
    path(
        "requests/<int:pk>/withdraw", v.WithdrawLeaveView.as_view(), name="leave-request-withdraw"
    ),
    path("requests/<int:pk>/cancel", v.CancelLeaveView.as_view(), name="leave-request-cancel"),
    path("requests/<int:pk>/extend", v.ExtendLeaveView.as_view(), name="leave-request-extend"),
    path(
        "requests/<int:pk>/renominate",
        v.RenominateSubstituteView.as_view(),
        name="leave-request-renominate",
    ),
    path(
        "requests/<int:pk>/resumption",
        v.SubmitResumptionView.as_view(),
        name="leave-request-resumption",
    ),
    path("requests/<int:pk>/trail", v.LeaveTrailView.as_view(), name="leave-request-trail"),
    # substitute nominations
    path("nominations", v.NominationsListView.as_view(), name="leave-nominations"),
    path(
        "nominations/<int:pk>/respond",
        v.RespondNominationView.as_view(),
        name="leave-nomination-respond",
    ),
    # workflow queues and decisions
    path("review", v.ReviewQueueView.as_view(), name="leave-review-queue"),
    path("review/<int:pk>", v.ReviewDecisionView.as_view(), name="leave-review-decision"),
    path("routing", v.RoutingQueueView.as_view(), name="leave-routing-queue"),
    path("routing/<int:pk>", v.RoutingDecisionView.as_view(), name="leave-routing-decision"),
    path("sanction", v.SanctionQueueView.as_view(), name="leave-sanction-queue"),
    path("sanction/<int:pk>", v.SanctionDecisionView.as_view(), name="leave-sanction-decision"),
    path("resumptions", v.ResumptionsQueueView.as_view(), name="leave-resumptions-queue"),
    path(
        "resumptions/<int:pk>/verify",
        v.VerifyResumptionView.as_view(),
        name="leave-resumption-verify",
    ),
    # institute leave balances and offline entry
    path("balances", v.InstituteBalancesView.as_view(), name="leave-balances"),
    path("admin/offline", v.RecordOfflineView.as_view(), name="leave-admin-offline"),
    # policy administration
    path("admin/policies", v.AdminPoliciesView.as_view(), name="leave-admin-policies"),
    path(
        "admin/policies/<int:pk>/publish",
        v.AdminPolicyPublishView.as_view(),
        name="leave-admin-policy-publish",
    ),
    path(
        "admin/policies/<int:pk>/readiness",
        v.AdminPolicyReadinessView.as_view(),
        name="leave-admin-policy-readiness",
    ),
    path(
        "admin/policies/<int:pk>/rules",
        v.AdminPolicyRulesView.as_view(),
        name="leave-admin-policy-rules",
    ),
    path(
        "admin/policies/<int:pk>/authority",
        v.AdminPolicyAuthorityView.as_view(),
        name="leave-admin-policy-authority",
    ),
    path(
        "admin/policies/<int:pk>/sla", v.AdminPolicySlaView.as_view(), name="leave-admin-policy-sla"
    ),
    # calendar administration
    path("admin/calendars", v.AdminCalendarsView.as_view(), name="leave-admin-calendars"),
    path(
        "admin/calendars/<int:pk>/publish",
        v.AdminCalendarPublishView.as_view(),
        name="leave-admin-calendar-publish",
    ),
    path(
        "admin/calendars/<int:pk>/holidays",
        v.AdminCalendarHolidaysView.as_view(),
        name="leave-admin-calendar-holidays",
    ),
    path(
        "admin/calendars/<int:pk>/vacations",
        v.AdminCalendarVacationsView.as_view(),
        name="leave-admin-calendar-vacations",
    ),
]
