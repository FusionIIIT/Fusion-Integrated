"""HTTP boundary for ELM; authorization and state changes stay in services."""
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant
from modules.elm.api import serializers as s
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    LeaveAccount,
    LeaveCalendarDate,
    LeaveCase,
    LeavePolicy,
    LeaveRequest,
    OrganizationUnit,
)
from modules.elm.services import leave_management as service

MODULE = HasModuleGrant("elm")


def _actor(request):
    return request.principal


def _require(actor, permission):
    check = getattr(actor, "has_permission", None)
    if not check or not check(permission):
        from core.api.exceptions import PermissionDeniedError

        raise PermissionDeniedError("This action is not permitted.")


def _leave_payload(leave):
    return {
        **s.LeaveRequestSerializer(leave).data,
        "cases": s.LeaveCaseSerializer(leave.cases.all(), many=True).data,
        "history": s.LeaveAuditEventSerializer(
            leave.audit_events.all(), many=True).data,
        "transactions": s.LeaveTransactionSerializer(
            leave.transactions.all(), many=True).data,
    }


class LeaveSummaryView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        actor = _actor(request)
        _require(actor, "elm.leave.view_self")
        profile = service._profile(actor.user_id)
        year = timezone.localdate().year
        accounts = [
            s.LeaveAccountSerializer(service._account(
                actor.user_id, policy.category, year, profile.employee_type)).data
            for policy in LeavePolicy.objects.filter(is_active=True)
        ]
        pending = LeaveRequest.objects.filter(
            applicant_user_id=actor.user_id,
            status__in=("awaiting_substitute", "pending_unit_head", "pending_sanction"),
        ).count()
        return Response({
            "employee": s.EmployeeProfileSerializer(profile).data,
            "year": year,
            "balances": accounts,
            "pending_requests": pending,
        })


class LeaveRequestListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        _require(actor, "elm.leave.view_self")
        qs = LeaveRequest.objects.filter(applicant_user_id=actor.user_id)
        return Response(_leave_payload_list(qs))

    @extend_schema(request=s.LeaveRequestCreateSerializer,
                   responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        data = s.LeaveRequestCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        leave = service.apply_for_leave(_actor(request), data.validated_data)
        return Response(_leave_payload(leave), status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(APIView):
    permission_classes = [MODULE]

    def get(self, request, pk):
        leave = service.request_for_actor(_actor(request), pk)
        return Response(_leave_payload(leave))


class LeaveActionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        leave = service.request_for_actor(_actor(request), pk)
        data = s.DecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        updated = service.decide_leave(
            _actor(request), leave, data.validated_data["action"],
            data.validated_data["note"])
        return Response(_leave_payload(updated))


class LeaveWithdrawView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        leave = service.request_for_actor(_actor(request), pk)
        return Response(_leave_payload(service.withdraw(_actor(request), leave)))


class SubstituteReplaceView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        leave = service.request_for_actor(_actor(request), pk)
        data = s.SubstituteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        updated = service.replace_substitute(
            _actor(request), leave, data.validated_data["substitute_user_id"])
        return Response(_leave_payload(updated))


class LeaveCaseListCreateView(APIView):
    permission_classes = [MODULE]

    def get(self, request, pk):
        leave = service.request_for_actor(_actor(request), pk)
        return Response(s.LeaveCaseSerializer(leave.cases.all(), many=True).data)

    @extend_schema(request=s.LeaveCaseCreateSerializer,
                   responses={201: s.LeaveCaseSerializer})
    def post(self, request, pk):
        leave = service.request_for_actor(_actor(request), pk)
        data = s.LeaveCaseCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        attrs = dict(data.validated_data)
        case_type = attrs.pop("case_type")
        case = service.create_case(_actor(request), leave, case_type, attrs)
        return Response(s.LeaveCaseSerializer(case).data,
                        status=status.HTTP_201_CREATED)


class LeaveCaseActionView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        case = service._case_for_actor(_actor(request), pk)
        data = s.DecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        updated = service.decide_case(
            _actor(request), case, data.validated_data["action"],
            data.validated_data["note"])
        return Response(s.LeaveCaseSerializer(updated).data)


class LeaveCaseWithdrawView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        case = service._case_for_actor(_actor(request), pk)
        return Response(s.LeaveCaseSerializer(
            service.withdraw_case(_actor(request), case)).data)


class LeaveCaseSubstituteView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        case = service._case_for_actor(_actor(request), pk)
        data = s.SubstituteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        case = service.replace_case_substitute(
            _actor(request), case, data.validated_data["substitute_user_id"])
        return Response(s.LeaveCaseSerializer(case).data)


class LeaveInboxView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        actor = _actor(request)
        permissions = getattr(actor, "permissions", ())
        requests = LeaveRequest.objects.filter(
            status__in=("awaiting_substitute", "pending_unit_head", "pending_sanction"),
        ).filter(
            service_query(actor, permissions, "assigned_permission"))
        cases = LeaveCase.objects.select_related("leave_request").filter(
            status__in=("awaiting_substitute", "pending_unit_head", "pending_sanction"),
        ).filter(service_query(actor, permissions, "assigned_permission"))
        return Response({
            "requests": _leave_payload_list(requests),
            "cases": s.LeaveCaseSerializer(cases, many=True).data,
        })


def service_query(actor, permissions, field):
    from django.db.models import Q

    query = Q(assigned_user_id=actor.user_id)
    if permissions:
        roles = getattr(actor, "roles", ())
        query |= (
            Q(**{f"{field}__in": list(permissions)})
            & (Q(assigned_role="") | Q(assigned_role__in=list(roles)))
        )
    return query


def _leave_payload_list(queryset):
    return [_leave_payload(leave) for leave in queryset]


class LeaveAccountsView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        actor = _actor(request)
        check = getattr(actor, "has_permission", None)
        if not check or not check("elm.leave.view_all"):
            _require(actor, "elm.leave.view_self")
            qs = LeaveAccount.objects.filter(user_id=actor.user_id)
        else:
            qs = LeaveAccount.objects.all()
            user_id = request.query_params.get("user_id")
            year = request.query_params.get("year")
            if user_id:
                qs = qs.filter(user_id=user_id)
            if year:
                qs = qs.filter(year=year)
        return Response(s.LeaveAccountSerializer(qs.order_by(
            "-year", "user_id", "category"), many=True).data)

    def post(self, request):
        data = s.AccountAdjustmentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        account = service.adjust_account(_actor(request), **data.validated_data)
        return Response(s.LeaveAccountSerializer(account).data)


class OfflineLeaveRecordView(APIView):
    permission_classes = [MODULE]

    def post(self, request):
        data = s.OfflineLeaveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        leave = service.record_offline_leave(_actor(request), data.validated_data)
        return Response(_leave_payload(leave), status=status.HTTP_201_CREATED)


class LeavePolicyListView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        return Response(s.LeavePolicySerializer(
            LeavePolicy.objects.all(), many=True).data)


class LeavePolicyDetailView(APIView):
    permission_classes = [MODULE]

    def patch(self, request, category):
        _require(_actor(request), "elm.config.manage")
        policy = LeavePolicy.objects.filter(category=category).first()
        if policy is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("Leave policy not found.")
        data = s.LeavePolicySerializer(policy, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(data.data)


class LeaveCalendarView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        qs = LeaveCalendarDate.objects.all()
        actor = _actor(request)
        check = getattr(actor, "has_permission", None)
        if (request.query_params.get("published") == "true"
                or not check or not check("elm.calendar.manage")):
            qs = qs.filter(is_published=True)
        return Response(s.LeaveCalendarSerializer(qs, many=True).data)

    def post(self, request):
        _require(_actor(request), "elm.calendar.manage")
        data = s.LeaveCalendarSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        calendar_date = data.save()
        return Response(s.LeaveCalendarSerializer(calendar_date).data,
                        status=status.HTTP_201_CREATED)


class LeaveCalendarPublishView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        _require(_actor(request), "elm.calendar.manage")
        calendar_date = LeaveCalendarDate.objects.filter(pk=pk).first()
        if calendar_date is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("Calendar entry not found.")
        calendar_date.is_published = True
        calendar_date.published_at = timezone.now()
        calendar_date.published_by_user_id = _actor(request).user_id
        calendar_date.save(update_fields=[
            "is_published", "published_at", "published_by_user_id", "updated_at",
        ])
        return Response(s.LeaveCalendarSerializer(calendar_date).data)


class OrganizationUnitListView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        _require(_actor(request), "elm.config.manage")
        return Response(s.OrganizationUnitSerializer(
            OrganizationUnit.objects.all(), many=True).data)

    def post(self, request):
        _require(_actor(request), "elm.config.manage")
        data = s.OrganizationUnitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(data.data, status=status.HTTP_201_CREATED)


class EmployeeProfileListView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        _require(_actor(request), "elm.config.manage")
        return Response(s.EmployeeProfileSerializer(
            EmployeeProfile.objects.all(), many=True).data)

    def post(self, request):
        _require(_actor(request), "elm.config.manage")
        data = s.EmployeeProfileSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(data.data, status=status.HTTP_201_CREATED)


class ApprovalRouteListView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        _require(_actor(request), "elm.config.manage")
        return Response(s.ApprovalRouteSerializer(
            ApprovalRoute.objects.all(), many=True).data)

    def post(self, request):
        _require(_actor(request), "elm.config.manage")
        data = s.ApprovalRouteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(data.data, status=status.HTTP_201_CREATED)


class YearEndProcessView(APIView):
    permission_classes = [MODULE]

    def post(self, request):
        year = request.data.get("year")
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            from core.api.exceptions import BadRequestError

            raise BadRequestError("year must be a number.",
                                  code="invalid_year") from exc
        return Response(service.process_year_end(_actor(request), year))
