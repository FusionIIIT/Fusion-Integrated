from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.elm.api.serializers import LeaveRequestSerializer
from modules.elm.services import leave_requests, workflow


def current_employee(request):
    principal = getattr(request, "principal", None)
    user_id = getattr(principal, "user_id", None) if principal else None
    if user_id is None:
        user_id = request.user.pk
    return get_object_or_404(get_user_model(), pk=user_id)


class MyLeaveRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = current_employee(request)
        rows = leave_requests.list_employee_requests(employee=employee)
        return Response({
            "results": LeaveRequestSerializer(rows, many=True).data
        })

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = current_employee(request)

        leave = leave_requests.create_leave_request(
            employee=employee,
            **serializer.validated_data,
        )
        return Response(
            LeaveRequestSerializer(leave).data,
            status=status.HTTP_201_CREATED,
        )


class MyLeaveActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        employee = current_employee(request)

        # Confirm ownership before attempting any action.
        get_object_or_404(
            get_user_model().objects.filter(pk=employee.pk),
            elm_leave_requests__pk=pk,
        )

        try:
            if action == "withdraw":
                leave = workflow.withdraw_request(
                    request_id=pk, employee=employee
                )
            elif action == "cancel":
                leave = workflow.cancel_approved_request(
                    request_id=pk, employee=employee
                )
            else:
                return Response(
                    {"detail": "Unknown action."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(LeaveRequestSerializer(leave).data)
