from django.urls import include, path
urlpatterns = [path("api/v1/complaints/", include("modules.complaint_cms.api.urls"))]
