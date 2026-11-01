"""Authentication and session management views for Super Admin operators."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import AllowAny
from modules.system_admin.api.serializers import (
    SuperAdminLoginSerializer,
    SuperAdminLogoutSerializer,
)
from modules.system_admin.services import (
    authenticate_super_admin,
    terminate_session,
)


class SuperAdminLoginView(APIView):
    """UC-SA-033: Authenticate Super Admin and Establish Session (AFR-SA-073A..C, AFR-SA-074A..C)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = authenticate_super_admin(
            user_id=1,  # Operator user ID
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            two_factor_code=serializer.validated_data["two_factor_code"],
            ip_address=request.META.get("REMOTE_ADDR", "127.0.0.1"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response({
            "session_key": session.session_key,
            "created_at": session.created_at,
            "message": "Super Admin session established with 2FA.",
        }, status=status.HTTP_200_OK)


class SuperAdminLogoutView(APIView):
    """UC-SA-034: Terminate Super Admin Session."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = terminate_session(
            session_key=serializer.validated_data["session_key"],
            actor_user_id=getattr(request.principal, "erp_user_id", 1),
            actor_username=getattr(request.principal, "username", "operator"),
        )
        return Response({"terminated": success})
