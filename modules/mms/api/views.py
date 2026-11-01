from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.mms.api import serializers as s
from modules.mms.selectors import registrations as sel
from modules.mms.services import registrations as svc

MODULE = HasModuleGrant("mms")


class MyRegistrationRequestsView(generics.ListAPIView):
    permission_classes = [
        MODULE,
        HasPermission(
            "mms.registration.view_self",
            "mms.registration.view",
            require_all=False,
        ),
    ]
    serializer_class = s.RegistrationRequestSerializer

    def get_queryset(self):
        return sel.visible_requests(self.request.principal)


class SubmitRegistrationView(APIView):
    permission_classes = [MODULE, HasPermission("mms.registration.create")]

    def post(self, request):
        ser = s.SubmitRegistrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        result = svc.submit_registration(
            student_user_id=request.principal.user_id,
            window_id=d["window_id"],
            remarks=d["remarks"],
        )
        return Response(
            s.RegistrationRequestSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class DecideRegistrationView(APIView):
    permission_classes = [MODULE, HasPermission("mms.registration.review")]

    def post(self, request, pk: int):
        ser = s.DecideRegistrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        result = svc.decide_registration(
            request_id=pk,
            decision=d["decision"],
            decided_by_user_id=request.principal.user_id,
            decision_note=d["decision_note"],
        )
        return Response(s.RegistrationRequestSerializer(result).data)
