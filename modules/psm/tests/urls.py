from django.urls import include, path

urlpatterns = [path("api/v1/psm/", include("modules.psm.api.urls"))]
