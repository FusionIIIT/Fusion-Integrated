from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import LeaveApplication, LeaveBalance
from modules.elm.services.submission import (
    respond_to_substitute,
    submit_leave,
    withdraw_leave,
)

from .serializers import (
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveSubstituteResponseSerializer,
)


class LeaveApplicationListView(generics.ListAPIView):
    serializer_class = LeaveApplicationSerializer
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave.view_self"),
    ]

    def get_queryset(self):
        actor = self.request.principal
        return LeaveApplication.objects.filter(
            applicant_user_id=actor.user_id
        )


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave.view_self"),
    ]

    def get_queryset(self):
        actor = self.request.principal
        return LeaveBalance.objects.filter(user_id=actor.user_id)


class LeaveApplicationCreateView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave.apply"),
    ]

    def post(self, request):
        actor = request.principal
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = LeaveApplication(
            applicant_user_id=actor.user_id,
            **serializer.validated_data,
        )

        try:
            submit_leave(application, actor)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc

        return Response(
            LeaveApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave.withdraw_self"),
    ]

    def post(self, request, application_id):
        application = withdraw_leave(
            application_id=application_id,
            actor=request.principal,
        )
        return Response(
            LeaveApplicationSerializer(application).data,
            status=status.HTTP_200_OK,
        )


class LeaveSubstituteResponseView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave.substitute_respond"),
    ]

    def post(self, request, application_id):
        serializer = LeaveSubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = respond_to_substitute(
            application_id=application_id,
            actor=request.principal,
            response=serializer.validated_data["response"],
        )
        return Response(
            LeaveApplicationSerializer(application).data,
            status=status.HTTP_200_OK,
        )
