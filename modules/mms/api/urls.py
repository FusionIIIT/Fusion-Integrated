from django.urls import path

from modules.mms.api import views as v

urlpatterns = [
    path("registrations", v.MyRegistrationRequestsView.as_view(), name="mms-registrations"),
    path(
        "registrations/submit",
        v.SubmitRegistrationView.as_view(),
        name="mms-registration-submit",
    ),
    path(
        "registrations/<int:pk>/decide",
        v.DecideRegistrationView.as_view(),
        name="mms-registration-decide",
    ),
]
