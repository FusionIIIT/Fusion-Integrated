from django.urls import include, path
urlpatterns = [path("api/v1/leave/", include("modules.leave_elm.api.urls"))]
