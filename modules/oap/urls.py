from rest_framework.routers import DefaultRouter
from modules.oap.views import StudentLeaveViewSet, BonafideViewSet, NoDuesViewSet, NoDuesItemViewSet, PGAssistantshipViewSet, GraduateSeminarViewSet

# Create a router instance
router = DefaultRouter()

# Register each viewset under the 'oap' namespace
router.register('leave', StudentLeaveViewSet)
router.register('bonafide', BonafideViewSet)
router.register('nodues', NoDuesViewSet)
router.register('nodues-items', NoDuesItemViewSet)
router.register('assistantship', PGAssistantshipViewSet)
router.register('seminar', GraduateSeminarViewSet)

# Set the app name for the router
router.app_name = 'oap'

# Export the URL patterns
urlpatterns = router.urls