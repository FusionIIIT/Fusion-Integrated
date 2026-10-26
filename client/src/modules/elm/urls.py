from django.urls import path, include

urlpatterns = [
    path('elm/', include('modules.elm.urls')),
]
