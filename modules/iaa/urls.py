from django.urls import path

from modules.iaa import views as v

urlpatterns = [
    path("requests", v.RequestListCreateView.as_view(), name="iaa-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="iaa-request"),
    path("requests/<int:pk>/submit", v.SubmitView.as_view(), name="iaa-request-submit"),
    path("requests/<int:pk>/validate", v.ValidateView.as_view(),
         name="iaa-request-validate"),
    path("requests/<int:pk>/decide", v.DecideView.as_view(), name="iaa-request-decide"),
    path("requests/<int:pk>/record", v.RecordView.as_view(), name="iaa-request-record"),
]
