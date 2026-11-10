from django.urls import path

from .views import ELMDataViewSet

urlpatterns = [
    path('', ELMDataViewSet.as_view({'get': 'list'})),
]
