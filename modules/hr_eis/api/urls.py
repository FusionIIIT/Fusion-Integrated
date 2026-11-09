from django.urls import path, include
from rest_framework.routers import DefaultRouter
from modules.hr_eis.api.views import EmployeeViewSet, DepartmentViewSet, PositionViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'positions', PositionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
