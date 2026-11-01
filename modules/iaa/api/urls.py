from django.urls import path
from modules.iaa.api import views as v
urlpatterns = [
 path("requests", v.ExpenseListCreateView.as_view(), name="iaa-requests"),
 path("requests/<int:pk>", v.ExpenseDetailView.as_view(), name="iaa-request-detail"),
 path("requests/<int:pk>/submit", v.ExpenseSubmitView.as_view(), name="iaa-request-submit"),
 path("requests/<int:pk>/decision", v.ExpenseDecisionView.as_view(), name="iaa-request-decision"),
 path("requests/<int:pk>/approvals", v.ApprovalHistoryView.as_view(), name="iaa-request-approvals"),
 path("travel-claims", v.TravelListCreateView.as_view(), name="iaa-travel-claims"),
 path("travel-claims/<int:pk>/submit", v.TravelSubmitView.as_view(), name="iaa-travel-submit"),
 path("anomalies", v.AnomalyListCreateView.as_view(), name="iaa-anomalies"),
 path("audit-observations", v.ObservationListCreateView.as_view(), name="iaa-audit-observations"),
 path("policies", v.PolicyListCreateView.as_view(), name="iaa-policies"),
 path("audit-events", v.AuditEventsView.as_view(), name="iaa-audit-events"),
]
