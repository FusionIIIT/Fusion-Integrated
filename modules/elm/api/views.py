from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant
from modules.elm.api import serializers as s
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    OrganizationUnit,
)
from modules.elm.selectors.requests import visible_to
from modules.elm.services import workflow

MODULE = HasModuleGrant("elm")


def _actor(request):
    return request.principal


def _require(actor, code):
    if not actor.has_permission(code):
        raise PermissionDenied("You do not have permission to perform this ELM action.")


def _request_scope(actor):
    qs = visible_to(actor)
    if not qs.exists():
        # Empty collections are valid for a scoped user. Authorization is checked
        # separately so an empty result does not turn into an authorization error.
        if any(
            actor.has_permission(code)
            for code in (
                "elm.leave_request.view_self",
                "elm.workflow.view",
                "elm.substitute.respond",
                "elm.record.manage",
            )
        ):
            return qs
        raise PermissionDenied("You do not have permission to view ELM records.")
    return qs


class BalanceView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        _require(_actor(request), "elm.leave_request.view_self")
        year = request.query_params.get("year")
        if year:
            try:
                year = int(year)
            except ValueError as exc:
                raise ValidationError({"year": "Year must be a number."}) from exc
        return Response(workflow.balances_for(_actor(request).user_id, year))


class RequestListCreateView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        qs = _request_scope(_actor(request))
        if request.query_params.get("queue") == "true":
            qs = qs.filter(assigned_user_id=_actor(request).user_id, status__in=workflow.PENDING)
        return Response(
            s.LeaveRequestReadSerializer(qs, many=True, context={"actor": _actor(request)}).data
        )

    def post(self, request):
        actor = _actor(request)
        _require(actor, "elm.leave_request.create")
        payload = s.SubmitLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data, actor=actor)
        obj = workflow.submit_leave(actor.user_id, data)
        return Response(
            s.LeaveRequestReadSerializer(obj, context={"actor": actor}).data,
            status=status.HTTP_201_CREATED,
        )


class RequestDetailView(APIView):
    permission_classes = [MODULE]

    def get_object(self, request, pk):
        try:
            obj = _request_scope(_actor(request)).get(pk=pk)
        except LeaveRequest.DoesNotExist as exc:
            raise Http404 from exc
        return obj

    def get(self, request, pk):
        obj = self.get_object(request, pk)
        return Response(s.LeaveRequestReadSerializer(obj, context={"actor": _actor(request)}).data)

    def post(self, request, pk):
        actor = _actor(request)
        payload = s.ActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        action = data["action"]
        obj = self.get_object(request, pk)
        if action == "withdraw":
            _require(actor, "elm.leave_request.withdraw")
        elif action in ("accept_substitute", "decline_substitute", "replace_substitute"):
            _require(actor, "elm.substitute.respond")
        elif action in ("recommended", "not_recommended"):
            _require(actor, "elm.workflow.review")
        elif action == "verify":
            _require(actor, "elm.workflow.route")
        elif action in ("approve", "reject"):
            _require(
                actor,
                "elm.workflow.review"
                if obj.assigned_stage == "unit_head"
                else "elm.workflow.sanction",
            )
        result = workflow.act(
            actor.user_id, obj.pk, action, data.get("note", ""), data.get("substitute_user_id")
        )
        return Response(s.LeaveRequestReadSerializer(result, context={"actor": actor}).data)


class AdminDataView(APIView):
    """Configuration and record endpoints are permission-gated on the server."""

    permission_classes = [MODULE]
    resources = {
        "policies": (LeavePolicy, s.LeavePolicySerializer, "elm.configuration.manage"),
        "units": (OrganizationUnit, s.OrganizationUnitSerializer, "elm.configuration.manage"),
        "employees": (EmployeeProfile, s.EmployeeProfileSerializer, "elm.configuration.manage"),
        "routes": (ApprovalRoute, s.ApprovalRouteSerializer, "elm.configuration.manage"),
        "calendars": (HolidayCalendar, s.HolidayCalendarSerializer, "elm.calendar.manage"),
        "holidays": (Holiday, s.HolidaySerializer, "elm.calendar.manage"),
    }

    def _resource(self, request, name):
        try:
            model, serializer, permission = self.resources[name]
        except KeyError as exc:
            raise Http404 from exc
        _require(_actor(request), permission)
        return model, serializer

    def get(self, request, resource, pk=None):
        model, serializer = self._resource(request, resource)
        if pk is not None:
            try:
                return Response(serializer(model.objects.get(pk=pk)).data)
            except model.DoesNotExist as exc:
                raise Http404 from exc
        rows = model.objects.all()
        return Response(serializer(rows, many=True).data)

    def post(self, request, resource):
        model, serializer_cls = self._resource(request, resource)
        if resource == "policies" and request.data.get("category"):
            instance = model.objects.filter(category=request.data["category"]).first()
        else:
            instance = None
        payload = serializer_cls(instance, data=request.data, partial=instance is not None)
        payload.is_valid(raise_exception=True)
        if resource == "calendars" and payload.validated_data.get("status") == "published":
            raise ValidationError({"status": "Create a draft, add holidays, then publish it."})
        obj = payload.save()
        if resource == "calendars" and obj.status == "published" and not obj.published_at:
            obj.published_at = timezone.now()
            obj.save(update_fields=["published_at", "updated_at"])
        return Response(serializer_cls(obj).data, status=status.HTTP_201_CREATED)

    def put(self, request, resource, pk):
        model, serializer_cls = self._resource(request, resource)
        try:
            instance = model.objects.get(pk=pk)
        except model.DoesNotExist as exc:
            raise Http404 from exc
        payload = serializer_cls(instance, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        obj = payload.save()
        return Response(serializer_cls(obj).data)


class CalendarPublishView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor = _actor(request)
        _require(actor, "elm.calendar.manage")
        try:
            calendar = HolidayCalendar.objects.get(pk=pk)
        except HolidayCalendar.DoesNotExist as exc:
            raise Http404 from exc
        with transaction.atomic():
            HolidayCalendar.objects.filter(year=calendar.year, status="published").exclude(
                pk=pk
            ).update(status="archived")
            calendar.status = "published"
            calendar.published_at = timezone.now()
            calendar.save(update_fields=["status", "published_at", "updated_at"])
        return Response(s.HolidayCalendarSerializer(calendar).data)
