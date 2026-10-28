from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from modules.elm.api import serializers as s
from modules.elm.api.permissions import MODULE, permission
from modules.elm.selectors import configuration as config_selector
from modules.elm.selectors.requests import requests_for, tasks_for
from modules.elm.services import configuration as config_service
from modules.elm.services import requests as service

P_CREATE = permission("elm.request.create")
P_VIEW_SELF = permission("elm.request.view_self")
P_POLICY = permission("elm.policy.manage")
P_CALENDAR = permission("elm.calendar.manage")


class RequestListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True), operation_id="elm_requests_list")
    def get(self, request):
        actor = request.principal
        if not actor.has_any_permission(
            "elm.request.view_self",
            "elm.request.review",
            "elm.request.route",
            "elm.request.sanction",
            "elm.policy.manage",
            "elm.calendar.manage",
        ):
            raise PermissionDeniedError("This action needs an ELM request-view permission.")
        qs = requests_for(actor).order_by("-created_at")
        return Response(s.LeaveRequestSerializer(qs[:200], many=True).data)

    @extend_schema(
        request=s.LeaveRequestCreateSerializer,
        responses=s.LeaveRequestSerializer,
        operation_id="elm_requests_create",
    )
    def post(self, request):
        actor = request.principal
        data = s.LeaveRequestCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        req = service.create_request(actor=actor, data=data.validated_data)
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class RequestDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses=s.LeaveRequestSerializer, operation_id="elm_request_detail")
    def get(self, request, pk):
        req = requests_for(request.principal).filter(pk=pk).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        return Response(s.LeaveRequestSerializer(req).data)

    @extend_schema(
        request=s.LeaveRequestModifySerializer,
        responses=s.LeaveRequestSerializer,
        operation_id="elm_request_modify",
    )
    def patch(self, request, pk):
        data = s.LeaveRequestModifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        req = service.modify_request(
            actor=request.principal, request_id=pk, changes=data.validated_data
        )
        return Response(s.LeaveRequestSerializer(req).data)


class RelatedRequestView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.RelatedRequestSerializer,
        responses=s.LeaveRequestSerializer,
        operation_id="elm_related_request_create",
    )
    def post(self, request, pk):
        data = s.RelatedRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        kind = values.pop("kind")
        req = service.create_related_request(
            actor=request.principal, parent_id=pk, kind=kind, data=values
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class RequestTransitionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.TransitionSerializer,
        responses=s.LeaveRequestSerializer,
        operation_id="elm_request_transition",
    )
    def post(self, request, pk):
        data = s.TransitionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        req = service.transition_request(
            actor=request.principal,
            request_id=pk,
            target=data.validated_data["target"],
            reason=data.validated_data.get("reason", ""),
            recommendation=data.validated_data.get("recommendation", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.SubstituteResponseSerializer,
        responses=s.LeaveRequestSerializer,
        operation_id="elm_substitute_response",
    )
    def post(self, request, pk):
        data = s.SubstituteResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        req = service.respond_substitute(
            actor=request.principal, request_id=pk, accepted=data.validated_data["accepted"]
        )
        return Response(s.LeaveRequestSerializer(req).data)


class BalanceView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        responses=inline_serializer(
            name="ELMBalanceResponse",
            fields={
                "user_id": serializers.IntegerField(),
                "balances": serializers.DictField(child=serializers.CharField()),
            },
        ),
        operation_id="elm_balance_me",
    )
    def get(self, request):
        return Response(
            {
                "user_id": request.principal.user_id,
                "balances": service.balance_for(request.principal.user_id, request.principal),
            }
        )


class HistoryView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        responses=inline_serializer(
            name="ELMHistoryEvent",
            fields={
                "event_type": serializers.CharField(),
                "from_status": serializers.CharField(),
                "to_status": serializers.CharField(),
                "reason": serializers.CharField(),
                "created_at": serializers.DateTimeField(),
            },
            many=True,
        ),
        operation_id="elm_request_history",
    )
    def get(self, request, pk):
        req = requests_for(request.principal).filter(pk=pk).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        events = req.audit_events.all().order_by("created_at")
        return Response(
            [
                {
                    "event_type": e.event_type,
                    "from_status": e.from_status,
                    "to_status": e.to_status,
                    "reason": e.reason,
                    "created_at": e.created_at,
                }
                for e in events
            ]
        )


class PolicyListCreateView(APIView):
    permission_classes = [MODULE, P_POLICY]

    @extend_schema(responses=s.LeavePolicySerializer(many=True), operation_id="elm_policies_list")
    def get(self, request):
        return Response(s.LeavePolicySerializer(config_selector.policies(), many=True).data)

    @extend_schema(
        request=s.LeavePolicySerializer,
        responses=s.LeavePolicySerializer,
        operation_id="elm_policies_create",
    )
    def post(self, request):
        data = s.LeavePolicySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        policy = config_service.create_policy(**data.validated_data)
        return Response(s.LeavePolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class PolicyPublishView(APIView):
    permission_classes = [MODULE, P_POLICY]

    @extend_schema(
        request=None, responses=s.LeavePolicySerializer, operation_id="elm_policy_publish"
    )
    def post(self, request, pk):
        policy = config_service.publish_policy(policy_id=pk, actor=request.principal)
        return Response(s.LeavePolicySerializer(policy).data)


class CalendarListCreateView(APIView):
    permission_classes = [MODULE, P_CALENDAR]

    @extend_schema(
        responses=s.CalendarVersionSerializer(many=True), operation_id="elm_calendars_list"
    )
    def get(self, request):
        return Response(s.CalendarVersionSerializer(config_selector.calendars(), many=True).data)

    @extend_schema(
        request=s.CalendarVersionSerializer,
        responses=s.CalendarVersionSerializer,
        operation_id="elm_calendars_create",
    )
    def post(self, request):
        data = s.CalendarVersionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        calendar = config_service.create_calendar(**data.validated_data)
        return Response(s.CalendarVersionSerializer(calendar).data, status=status.HTTP_201_CREATED)


class CalendarPublishView(APIView):
    permission_classes = [MODULE, P_CALENDAR]

    @extend_schema(
        request=None, responses=s.CalendarVersionSerializer, operation_id="elm_calendar_publish"
    )
    def post(self, request, pk):
        calendar = config_service.publish_calendar(calendar_id=pk, actor=request.principal)
        return Response(s.CalendarVersionSerializer(calendar).data)


class MyTasksView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        responses=inline_serializer(
            name="ELMMyTask",
            fields={
                "id": serializers.IntegerField(),
                "request_id": serializers.IntegerField(),
                "task_type": serializers.CharField(),
                "due_at": serializers.DateTimeField(allow_null=True),
            },
            many=True,
        ),
        operation_id="elm_tasks_me",
    )
    def get(self, request):
        actor = request.principal
        qs = tasks_for(actor)
        return Response(
            [
                {
                    "id": t.id,
                    "request_id": t.request_id,
                    "task_type": t.task_type,
                    "due_at": t.due_at,
                }
                for t in qs.order_by("created_at")[:100]
            ]
        )
