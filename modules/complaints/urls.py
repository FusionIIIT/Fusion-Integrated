from django.urls import path

from modules.complaints.api import ComplaintSubmitView

urlpatterns = [path("", ComplaintSubmitView.as_view(), name="complaint-submit")]
