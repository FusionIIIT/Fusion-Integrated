from django.urls import path, include
from rest_framework.routers import DefaultRouter
from modules.hostel import views

router = DefaultRouter()
router.register(r'hostels', views.HostelViewSet)
router.register(r'warden-role-bindings', views.WardenRoleBindingViewSet)
router.register(r'caretaker-role-bindings', views.CaretakerRoleBindingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
