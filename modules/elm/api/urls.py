from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("applications/", v.Applications.as_view()),
    path("applications/<int:pk>/", v.ApplicationDetail.as_view()),
    path("applications/<int:pk>/actions/", v.Action.as_view()),
    path("applications/<int:pk>/lifecycle/", v.Lifecycle.as_view()),
    path("applications/<int:pk>/export/", v.Export.as_view()),
    path("applications/<int:pk>/correction/", v.Correction.as_view()),
    path("tasks/", v.Tasks.as_view()), path("accounts/", v.Accounts.as_view()),
    path("ledger/", v.Ledger.as_view()), path("employees/", v.Employees.as_view()),
    path("notifications/", v.Notifications.as_view()),
    path("notifications/<int:pk>/read/", v.ReadNotification.as_view()),
    path("configuration/", v.Configuration.as_view()),
    path("calendars/", v.Calendars.as_view()), path("offline/", v.Offline.as_view()),
]
