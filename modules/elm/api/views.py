"""Authenticated HTTP endpoints for the Employee Leave Management module."""

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.contracts import (
    approve_leave_application,
    process_unit_head_review,
    submit_leave_application,
    withdraw_leave_application,
)
from modules.elm.models import LeaveApplicationTransition
from modules.elm.selectors import (
    get_application,
    get_applications,
    get_employee_balance,
    get_leave_categories,
)

MODULE = HasModuleGrant("elm")
P_VIEW = "elm.application.view"
P_CREATE = "elm.application.create"
P_REVIEW = "elm.application.review"
P_SANCTION = "elm.application.sanction"
P_WITHDRAW = "elm.application.withdraw"


class LeaveApplicationInput(serializers.Serializer):
    leave_category_code = serializers.CharField(max_length=16)
    requested_start = serializers.DateField()
    requested_end = serializers.DateField()
    purpose = serializers.CharField(max_length=4000, allow_blank=False, trim_whitespace=True)
    halftype = serializers.ChoiceField(
        choices=("", "FIRST_HALF", "SECOND_HALF"), required=False, default=""
    )
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        if attrs["station_leave"] and not attrs["station_leave_details"].strip():
            raise serializers.ValidationError(
                {"station_leave_details": "Enter the station-leave destination/details."}
            )
        if not attrs["station_leave"]:
            attrs["station_leave_details"] = ""
        return attrs


class DecisionInput(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=("approve", "reject", "recommend", "not_recommend"))
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)


def _actor(request):
    return request.principal


def _application_json(app):
    return {
        "id": app.pk,
        "user_id": app.user_id,
        "leave_category_code": app.leave_category.code,
        "leave_category_label": app.leave_category.label,
        "requested_start": app.requested_start.isoformat(),
        "requested_end": app.requested_end.isoformat(),
        "purpose": app.purpose,
        "halftype": app.halftype,
        "station_leave": app.station_leave,
        "station_leave_details": app.station_leave_details,
        "status": app.status,
        "created_at": app.created_at.isoformat(),
    }


def _own_application(application_id, owner_id):
    app = get_application(application_id)
    if app is None or app.user_id != owner_id:
        raise NotFoundError("Leave application not found.")
    return app


class LeaveCategoryListView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def get(self, request):
        categories = get_leave_categories()
        return Response(
            [
                {
                    "code": category.code,
                    "label": category.label,
                    "entitlement_days": category.entitlement_days,
                    "carry_forward": category.carry_forward,
                    "continuous_counting": category.continuous_counting,
                }
                for category in categories
            ]
        )


class LeaveApplicationListView(APIView):
    def get_permissions(self):
        permission = P_CREATE if self.request.method == "POST" else P_VIEW
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        actor = _actor(request)
        return Response([_application_json(app) for app in get_applications(actor.user_id)])

    def post(self, request):
        actor = _actor(request)
        payload = LeaveApplicationInput(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        app = submit_leave_application(
            user_id=actor.user_id,
            employee_kind=actor.kind,
            category_code=data["leave_category_code"],
            start=data["requested_start"],
            end=data["requested_end"],
            purpose=data["purpose"],
            half_type=data["halftype"],
            station_leave=data["station_leave"],
            station_leave_details=data["station_leave_details"],
        )
        return Response(_application_json(app), status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, pk):
        return Response(_application_json(_own_application(pk, _actor(request).user_id)))


class LeaveApplicationTransitionView(APIView):
    def get_permissions(self):
        return [MODULE(), HasPermission(P_REVIEW, P_SANCTION)()]

    def post(self, request, pk):
        actor = _actor(request)
        payload = DecisionInput(data=request.data)
        payload.is_valid(raise_exception=True)
        outcome = payload.validated_data["outcome"]
        reason = payload.validated_data.get("reason", "")
        app = get_application(pk)
        if app is None:
            raise NotFoundError("Leave application not found.")

        if app.leave_category.code in {"CL", "RH"} or outcome in {"recommend", "not_recommend"}:
            if not actor.has_permission(P_REVIEW):
                raise PermissionDeniedError()
            app = process_unit_head_review(pk, outcome, actor.user_id, actor.display_name, reason)
        else:
            if not actor.has_permission(P_SANCTION):
                raise PermissionDeniedError()
            app = approve_leave_application(pk, outcome, actor.user_id, actor.display_name, reason)
        return Response(_application_json(app))


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk):
        app = withdraw_leave_application(pk, _actor(request).user_id)
        return Response(_application_json(app))


class LeaveApplicationHistoryView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, pk):
        app = _own_application(pk, _actor(request).user_id)
        transitions = LeaveApplicationTransition.objects.filter(application=app).order_by(
            "at", "pk"
        )
        return Response(
            {
                "application_id": app.pk,
                "transitions": [
                    {
                        "from_status": row.from_status,
                        "to_status": row.to_status,
                        "actor_label": row.actor_label,
                        "at": row.at.isoformat(),
                        "reason": row.reason,
                    }
                    for row in transitions
                ],
            }
        )


class EmployeeLeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission("elm.balance.view")]

    def get(self, request):
        actor = _actor(request)
        balances = get_employee_balance(actor.user_id)
        categories = get_leave_categories()
        applicable = [
            category
            for category in categories
            if (category.code != "VL" or actor.kind == "faculty")
            and (category.code != "EL" or actor.kind == "staff")
        ]
        return Response(
            {
                "user_id": actor.user_id,
                "balances": {
                    category.code: {
                        "leave_category_code": category.code,
                        "leave_category_label": category.label,
                        "remaining_days": str(
                            balances[category.code].remaining_days
                            if category.code in balances
                            else category.entitlement_days
                        ),
                        "used_days": str(
                            balances[category.code].used_days if category.code in balances else 0
                        ),
                        "entitlement_days": category.entitlement_days,
                        "carry_forward": category.carry_forward,
                    }
                    for category in applicable
                },
            }
        )


class LeaveHistoryListView(APIView):
    permission_classes = [MODULE, HasPermission("elm.history.view")]

    def get(self, request):
        return Response(
            [_application_json(app) for app in get_applications(_actor(request).user_id)]
        )
