from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import LeaveApplicationSubmitSerializer
from modules.elm.models import LeaveApplication, LeaveBalance
from modules.elm.services.workflow import (
    LeaveWorkflowAction,
    WorkflowTransitionError,
    transition,
)

MODULE = HasModuleGrant("elm")


def _actor(request):
    return getattr(request, "principal", None)


def _application_data(application):
    return {
        "id": application.pk,
        "category": application.category,
        "start_date": application.start_date.isoformat(),
        "end_date": application.end_date.isoformat(),
        "requested_days": str(application.requested_days),
        "purpose": application.purpose,
        "status": application.status,
        "half_day_portion": application.half_day_portion,
        "created_at": application.created_at.isoformat(),
        "updated_at": application.updated_at.isoformat(),
    }


class MyLeaveBalancesView(APIView):
    permission_classes = [MODULE, IsAuthenticated]

    def get(self, request):
        actor = _actor(request)
        year = timezone.localdate().year
        balances = LeaveBalance.objects.filter(user_id=actor.user_id, leave_year=year)
        return Response(
            {
                "leave_year": year,
                "results": [
                    {
                        "category": balance.category,
                        "annual_entitlement": str(balance.annual_entitlement),
                        "current_balance": str(balance.current_balance),
                    }
                    for balance in balances.order_by("category")
                ],
            }
        )


class MyLeaveApplicationsView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("elm.leave_application.submit"),
    ]

    def get(self, request):
        applications = LeaveApplication.objects.filter(user_id=_actor(request).user_id).order_by(
            "-created_at", "-pk"
        )
        return Response({"results": [_application_data(a) for a in applications]})

    def post(self, request):
        payload = LeaveApplicationSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        actor = _actor(request)
        is_director = getattr(actor, "active_role", None) == "director"

        try:
            with transaction.atomic():
                application = LeaveApplication.objects.create(
                    user_id=actor.user_id,
                    category=data["category"],
                    start_date=data["start_date"],
                    end_date=data["end_date"],
                    requested_days=data["requested_days"],
                    purpose=data["purpose"],
                    half_day_portion=data["half_day_portion"],
                )
                application = transition(
                    application.pk,
                    LeaveWorkflowAction.SUBMIT,
                    category=data["category"],
                    applicant_is_director=is_director,
                    actor=actor,
                )
        except WorkflowTransitionError as err:
            raise ConflictError(str(err), code="invalid_workflow_transition") from err

        return Response(_application_data(application), status=status.HTTP_201_CREATED)


class LeaveApplicationActionView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("elm.leave_application.withdraw"),
    ]

    def post(self, request, pk):
        actor = _actor(request)
        application = get_object_or_404(LeaveApplication, pk=pk, user_id=actor.user_id)
        action = request.data.get("action")
        if action != LeaveWorkflowAction.WITHDRAW:
            raise ConflictError("Only withdrawal is available here.", code="invalid_action")
        try:
            application = transition(
                application.pk,
                LeaveWorkflowAction.WITHDRAW,
                category=application.category,
                actor=actor,
            )
        except WorkflowTransitionError as err:
            raise ConflictError(str(err), code="invalid_workflow_transition") from err
        return Response(_application_data(application))
