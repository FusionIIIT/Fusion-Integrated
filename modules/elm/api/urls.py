from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    # Balances
    path("balances", v.MyLeaveBalancesView.as_view(), name="elm-balances"),

    # Applications (Employee)
    path("applications", v.MyLeaveApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>", v.LeaveApplicationDetailView.as_view(), name="elm-application-detail"),
    path("applications/<int:pk>/withdraw", v.WithdrawLeaveApplicationView.as_view(), name="elm-application-withdraw"),
    path("applications/<int:pk>/cancel", v.CancelLeaveApplicationView.as_view(), name="elm-application-cancel"),
    path("applications/<int:pk>/extend", v.ExtendLeaveApplicationView.as_view(), name="elm-application-extend"),
    path("applications/<int:pk>/resume", v.SubmitResumptionView.as_view(), name="elm-application-resume"),

    # Substitute actions
    path("substitutes/requests", v.SubstituteRequestsView.as_view(), name="elm-substitute-requests"),
    path("substitutes/requests/<int:pk>/respond", v.RespondSubstituteView.as_view(), name="elm-substitute-respond"),
    path("applications/<int:pk>/replace-substitute", v.ReplaceSubstituteView.as_view(), name="elm-replace-substitute"),

    # Review Queues
    path("approvals/unit-head", v.UnitHeadApprovalsQueueView.as_view(), name="elm-unit-head-queue"),
    path("approvals/unit-head/<int:pk>/review", v.UnitHeadReviewView.as_view(), name="elm-unit-head-review"),
    path("approvals/sanction", v.SanctioningQueueView.as_view(), name="elm-sanction-queue"),
    path("approvals/sanction/<int:pk>/review", v.SanctionReviewView.as_view(), name="elm-sanction-review"),

    # Admin & Scheduled Events
    path("admin/offline-leave", v.RecordOfflineLeaveView.as_view(), name="elm-record-offline"),
    path("admin/year-end-process", v.YearEndProcessView.as_view(), name="elm-year-end"),
    path("admin/sla-check", v.TriggerSLACheckView.as_view(), name="elm-sla-check"),
]
