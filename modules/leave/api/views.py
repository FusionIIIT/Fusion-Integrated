"""API views for Employee Leave Management."""

from __future__ import annotations

import datetime

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import (
    AuthorityRule,
    Calendar,
    CategoryRule,
    Holiday,
    LeaveRequest,
    LedgerEntry,
    Policy,
    SlaRule,
    VacationPeriod,
)
from modules.leave.selectors import scoping
from modules.leave.selectors.balances import get_user_balances_summary
from modules.leave.services import (
    apply,
    cancel,
    extend,
    offline,
    resumption,
    review,
    routing,
    sanction,
    substitute,
    withdraw,
)


class BaseLeaveView(APIView):
    pass


# -- Self / Employee Views ---------------------------------------------------


class MyRequestsView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]
    serializer_class = s.LeaveRequestSerializer
    queryset = LeaveRequest.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return scoping.my_requests_queryset(self.request.principal.user_id)


class MyBalancesView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: s.BalanceSerializer(many=True)})
    def get(self, request):
        year = datetime.date.today().year
        data = get_user_balances_summary(request.principal.user_id, year)
        res = [{"category": k, **v} for k, v in data.items()]
        return Response(res)


class MyStatementView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: s.LedgerEntrySerializer(many=True)})
    def get(self, request, category: str):
        year = datetime.date.today().year
        entries = LedgerEntry.objects.filter(
            user_id=request.principal.user_id, year=year, category=category
        ).order_by("created_at")
        return Response(s.LedgerEntrySerializer(entries, many=True).data)


class ApplyLeaveView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=s.ApplyLeaveSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        ser = s.ApplyLeaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        p = request.principal
        req = apply.submit_leave_request(
            user_id=p.user_id,
            category=vd["category"],
            starts_on=vd["starts_on"],
            ends_on=vd["ends_on"],
            reason=vd["reason"],
            half=vd.get("half", "none"),
            evidence_reference=vd.get("evidence_reference", ""),
            substitute_user_id=vd.get("substitute_user_id"),
            station=vd.get("station"),
            is_faculty=getattr(p, "kind", "") == "faculty",
            designation=getattr(p, "active_role", ""),
            unit="",
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveDetailView(generics.RetrieveAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]
    serializer_class = s.LeaveRequestSerializer
    queryset = LeaveRequest.objects.all()

    def get_object(self):
        obj = super().get_object()
        p = self.request.principal
        if obj.user_id != p.user_id and not p.has_any_permission(
            "leave.request.review",
            "leave.request.route",
            "leave.request.sanction",
            "leave.substitute.respond",
        ):
            raise NotFoundError("Leave request not found.")
        return obj


class WithdrawLeaveView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.withdraw")]

    @extend_schema(request=s.RemarkSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.RemarkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = withdraw.withdraw_leave_request(
            request_id=pk,
            user_id=request.principal.user_id,
            remark=ser.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class CancelLeaveView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=s.RemarkSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.RemarkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = cancel.request_cancellation(
            request_id=pk,
            user_id=request.principal.user_id,
            remark=ser.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ExtendLeaveView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=s.ExtensionSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.ExtensionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        req = extend.request_extension(
            request_id=pk,
            user_id=request.principal.user_id,
            new_end=vd["new_end"],
            substitute_user_id=vd.get("substitute_user_id"),
            remark=vd.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class RenominateSubstituteView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=s.RenominateSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.RenominateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = substitute.renominate_substitute(
            request_id=pk,
            user_id=request.principal.user_id,
            new_substitute_id=ser.validated_data["substitute_user_id"],
        )
        return Response(s.LeaveRequestSerializer(req).data)


class SubmitResumptionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=s.ResumptionSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.ResumptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        req = resumption.submit_resumption(
            request_id=pk,
            user_id=request.principal.user_id,
            resumed_on=vd["resumed_on"],
            remark=vd.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class LeaveTrailView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: s.LeaveTransitionSerializer(many=True)})
    def get(self, request, pk: int):
        req = LeaveRequest.objects.filter(pk=pk).first()
        if not req:
            raise NotFoundError("Leave request not found.")
        transitions = req.transitions.all().order_by("created_at")
        return Response(s.LeaveTransitionSerializer(transitions, many=True).data)


# -- Substitute Views --------------------------------------------------------


class NominationsListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.substitute.respond")]
    serializer_class = s.LeaveRequestSerializer
    queryset = LeaveRequest.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return scoping.substitute_nominations_queryset(self.request.principal.user_id)


class RespondNominationView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.substitute.respond")]

    @extend_schema(
        request=s.SubstituteResponseSerializer, responses={200: s.LeaveRequestSerializer}
    )
    def post(self, request, pk: int):
        ser = s.SubstituteResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        req = substitute.respond_substitute_nomination(
            request_id=pk,
            substitute_user_id=request.principal.user_id,
            accepted=vd["accepted"],
            remark=vd.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


# -- Queues and Decision Views -----------------------------------------------


class ReviewQueueView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.review")]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        return scoping.review_queue_queryset()


class ReviewDecisionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.review")]

    @extend_schema(request=s.DecisionSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        req = review.review_leave_request(
            request_id=pk,
            reviewer_user_id=request.principal.user_id,
            reviewer_role=getattr(request.principal, "active_role", "Unit Head"),
            approve=vd["approve"],
            remark=vd.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class RoutingQueueView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.route")]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        return scoping.routing_queue_queryset()


class RoutingDecisionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.route")]

    @extend_schema(request=s.RemarkSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.RemarkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = routing.route_leave_request(
            request_id=pk,
            actor_user_id=request.principal.user_id,
            actor_role=getattr(request.principal, "active_role", "Establishment"),
            remark=ser.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class SanctionQueueView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.sanction")]
    serializer_class = s.LeaveRequestSerializer
    queryset = LeaveRequest.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        desig = getattr(self.request.principal, "active_role", None)
        return scoping.sanction_queue_queryset(desig)


class SanctionDecisionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.sanction")]

    @extend_schema(request=s.DecisionSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        req = sanction.sanction_leave_request(
            request_id=pk,
            actor_user_id=request.principal.user_id,
            actor_role=getattr(request.principal, "active_role", "Sanctioner"),
            approve=vd["approve"],
            remark=vd.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ResumptionsQueueView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.resumption.verify")]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        return scoping.resumption_queue_queryset()


class VerifyResumptionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.resumption.verify")]

    @extend_schema(request=s.RemarkSerializer, responses={200: s.LeaveRequestSerializer})
    def post(self, request, pk: int):
        ser = s.RemarkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = resumption.verify_resumption(
            request_id=pk,
            verifier_user_id=request.principal.user_id,
            verifier_role=getattr(request.principal, "active_role", "Authority"),
            remark=ser.validated_data.get("remark", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class InstituteBalancesView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.view")]

    @extend_schema(responses={200: s.BalanceSerializer(many=True)})
    def get(self, request):
        user_id_param = request.query_params.get("user_id")
        year = datetime.date.today().year
        uid = int(user_id_param) if user_id_param else request.principal.user_id
        data = get_user_balances_summary(uid, year)
        res = [{"category": k, **v} for k, v in data.items()]
        return Response(res)


# -- Admin / Policy / Calendar Views -----------------------------------------


class RecordOfflineView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.offline.record")]

    @extend_schema(request=s.OfflineRecordSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        ser = s.OfflineRecordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        req = offline.record_offline_leave(
            user_id=vd["user_id"],
            category=vd["category"],
            starts_on=vd["starts_on"],
            ends_on=vd["ends_on"],
            reason=vd["reason"],
            half=vd.get("half", "none"),
            faculty=vd.get("faculty", True),
            unit=vd.get("unit", ""),
            note=vd.get("note", ""),
            recorded_by_user_id=request.principal.user_id,
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class AdminPoliciesView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.policy.manage")]
    serializer_class = s.PolicySerializer
    queryset = Policy.objects.all().order_by("-effective_from")


class AdminPolicyPublishView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.policy.manage")]

    @extend_schema(request=None, responses={200: s.PolicySerializer})
    def post(self, request, pk: int):
        policy = Policy.objects.filter(pk=pk).first()
        if not policy:
            raise NotFoundError("Policy not found.")
        policy.published = True
        policy.save(update_fields=["published"])
        return Response(s.PolicySerializer(policy).data)


class AdminPolicyReadinessView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.policy.manage")]

    @extend_schema(responses={200: s.PolicyGapSerializer})
    def get(self, request, pk: int):
        policy = Policy.objects.filter(pk=pk).first()
        if not policy:
            raise NotFoundError("Policy not found.")
        gaps = []
        if not policy.category_rules.exists():
            gaps.append("No category rules defined.")
        if not policy.authority_rules.exists():
            gaps.append("No authority rules defined.")
        return Response({"ready": len(gaps) == 0, "gaps": gaps})


class AdminPolicyRulesView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.policy.manage")]
    serializer_class = s.CategoryRuleSerializer
    queryset = CategoryRule.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "pk" not in self.kwargs:
            return CategoryRule.objects.none()
        return CategoryRule.objects.filter(policy_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        serializer.save(policy_id=self.kwargs["pk"])


class AdminPolicyAuthorityView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.policy.manage")]
    serializer_class = s.AuthorityRuleSerializer
    queryset = AuthorityRule.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "pk" not in self.kwargs:
            return AuthorityRule.objects.none()
        return AuthorityRule.objects.filter(policy_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        serializer.save(policy_id=self.kwargs["pk"])


class AdminPolicySlaView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.policy.manage")]
    serializer_class = s.SlaRuleSerializer
    queryset = SlaRule.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "pk" not in self.kwargs:
            return SlaRule.objects.none()
        return SlaRule.objects.filter(policy_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        serializer.save(policy_id=self.kwargs["pk"])


class AdminCalendarsView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.calendar.manage")]
    serializer_class = s.CalendarSerializer
    queryset = Calendar.objects.all().order_by("-year")


class AdminCalendarPublishView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.calendar.manage")]

    @extend_schema(request=None, responses={200: s.CalendarSerializer})
    def post(self, request, pk: int):
        cal = Calendar.objects.filter(pk=pk).first()
        if not cal:
            raise NotFoundError("Calendar not found.")
        cal.published = True
        cal.save(update_fields=["published"])
        return Response(s.CalendarSerializer(cal).data)


class AdminCalendarHolidaysView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.calendar.manage")]
    serializer_class = s.HolidaySerializer
    queryset = Holiday.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "pk" not in self.kwargs:
            return Holiday.objects.none()
        return Holiday.objects.filter(calendar_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        serializer.save(calendar_id=self.kwargs["pk"])


class AdminCalendarVacationsView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.calendar.manage")]
    serializer_class = s.VacationPeriodSerializer
    queryset = VacationPeriod.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "pk" not in self.kwargs:
            return VacationPeriod.objects.none()
        return VacationPeriod.objects.filter(calendar_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        serializer.save(calendar_id=self.kwargs["pk"])
