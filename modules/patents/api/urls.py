from django.urls import path

from modules.patents.api import views as v

urlpatterns = [
    path("applications", v.ApplicationListView.as_view(), name="patents-applications"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(), name="patents-application"),
    path("applications/<int:pk>/inventors", v.InventorsView.as_view(), name="patents-inventors"),
    path("applications/<int:pk>/documents", v.DocumentUploadView.as_view(),
         name="patents-documents"),
    path("applications/<int:pk>/<str:action>", v.ApplicationActionView.as_view(),
         name="patents-application-action"),
    path("notifications", v.NotificationListView.as_view(), name="patents-notifications"),
    path("notifications/<int:nid>/read", v.NotificationReadView.as_view(),
         name="patents-notification-read"),
    path("reports/summary", v.SummaryView.as_view(), name="patents-summary"),
]
