from django.urls import include, path

app_name = "oap"

urlpatterns = [
    path("api/v1/oap/", include("modules.oap.api.urls")),
]
