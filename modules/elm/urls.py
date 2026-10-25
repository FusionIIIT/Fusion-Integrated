from django.urls import include, path

urlpatterns = [
    path("", include("modules.elm.api")),
]
