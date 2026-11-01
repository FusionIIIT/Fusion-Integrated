# modules/hr_eis/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeProfileViewSet, WorkExperienceViewSet

app_name = 'hr_eis'

router = DefaultRouter()
router.register(r'profiles', EmployeeProfileViewSet, basename='employee-profile')
router.register(r'experiences', WorkExperienceViewSet, basename='work-experience')

urlpatterns = [
    path('', include(router.urls)),
]