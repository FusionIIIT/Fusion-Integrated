from .views import LeaveAPI
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'mine', LeaveAPI, basename='leave')
