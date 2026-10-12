"""HTTP layer for the Employee Leave Management module.

Thin layer: parse, scope, delegate, serialise. Every read goes through a
selector; every write through a service. Ownership is enforced in the
selector, so an out-of-scope row is absent (404) rather than forbidden (403).
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.api.permissions import ScopedCollection
from modules.elm.models import (
    ELMPolicy,
    HolidayCalendar,
    HolidayEntry,
    LeaveApplication,
    LeaveBalance,
    LeaveDecision,
    LeaveSubstitution,
    Resumption,
    SLAConfiguration,
    VacationPeriod,
)
from modules.elm.models.roles import RoleGrant
from modules.elm.selectors import leave_applications_for as scoping

MODULE = HasModuleGrant("elm")

# Permission codes, seeded from the role catalogue.
P_VIEW_POLICY = "elm.leave_policy.view"
P_MANAGE_POLICY = "elm.leave_policy.manage"
P_MANAGE_HIERARCHY = "elm.leave_policy.hierarchy.manage"
P_MANAGE_CALENDAR = "elm.holiday_calendar.manage"
P_MANAGE_VACATION = "elm.vacation_period.manage"
P_APPLY = "elm.leave_application.apply"
P_VIEW = "elm.leave_application.view"
P_APPROVE = "elm.leave_application.approve"
P_VIEW_SELF = "elm.leave_application.view_self"
P_WITHDRAW = "elm.leave_application.withdraw"
P_CANCEL = "elm.leave_application.cancel"
P_MANAGE_BALANCE = "elm.leave_balance.manage"
P_MANAGE_ROLE = "elm.role.manage"
P_MANAGE_SLA = "elm.sla.manage"
P_MANAGE_OFFLINE = "elm.offline_leave.manage"


def _actor(request):
    return getattr(request, "principal", None)


# -- policy & hierarchy ------------------------------------------------------

class PolicyListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_POLICY)]

    @extend_schema(responses=s.ELMPolicySerializer(many=True))
    def get(self, request):
        return Response(list(ELMPolicy.objects.all().values()))

    @extend_schema(request=s.ELMPolicySerializer, responses=s.ELMPolicySerializer)
    def post(self, request):
        payload = s.ELMPolicySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        policy = ELMPolicy.objects.create(**payload.validated_data)
        return Response(s.ELMPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class PolicyDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_POLICY)]

    @extend_schema(responses=s.ELMPolicySerializer)
    def get(self, request, pk):
        try:
            policy = ELMPolicy.objects.get(pk=pk)
        except ELMPolicy.DoesNotExist:
            raise NotFoundError("No such policy.")
        return Response(s.ELMPolicySerializer(policy).data)

    @extend_schema(request=s.ELMPolicySerializer, responses=s.ELMPolicySerializer)
    def put(self, request, pk):
        payload = s.ELMPolicySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            policy = ELMPolicy.objects.get(pk=pk)
        except ELMPolicy.DoesNotExist:
            raise NotFoundError("No such policy.")
        for field, value in payload.validated_data.items():
            setattr(policy, field, value)
        policy.save()
        return Response(s.ELMPolicySerializer(policy).data)

    @extend_schema(request=s.ELMPolicySerializer, responses=s.ELMPolicySerializer)
    def patch(self, request, pk):
        return self.put(request, pk)


class PolicyHierarchyView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_HIERARCHY)]

    @extend_schema(responses=s.HierarchyLevelSerializer(many=True))
    def get(self, request, policy_pk):
        try:
            policy = ELMPolicy.objects.get(pk=policy_pk)
        except ELMPolicy.DoesNotExist:
            raise NotFoundError("No such policy.")
        return Response(list(policy.hierarchy_levels.values()))

    @extend_schema(request=s.HierarchyLevelSerializer, responses=s.HierarchyLevelSerializer)
    def post(self, request, policy_pk):
        payload = s.HierarchyLevelSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            policy = ELMPolicy.objects.get(pk=policy_pk)
        except ELMPolicy.DoesNotExist:
            raise NotFoundError("No such policy.")
        payload.validated_data["category"] = policy
        level = HierarchyLevel.objects.create(**payload.validated_data)
        return Response(s.HierarchyLevelSerializer(level).data, status=status.HTTP_201_CREATED)


class PolicyHierarchyDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_HIERARCHY)]

    @extend_schema(responses=s.HierarchyLevelSerializer)
    def get(self, request, policy_pk, level_pk):
        try:
            level = HierarchyLevel.objects.select_related("category").get(pk=level_pk)
        except HierarchyLevel.DoesNotExist:
            raise NotFoundError("No such hierarchy level.")
        if level.category_id != int(policy_pk):
            raise NotFoundError("No such hierarchy level.")
        return Response(s.HierarchyLevelSerializer(level).data)

    @extend_schema(request=s.HierarchyLevelSerializer, responses=s.HierarchyLevelSerializer)
    def put(self, request, policy_pk, level_pk):
        payload = s.HierarchyLevelSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            level = HierarchyLevel.objects.get(pk=level_pk)
        except HierarchyLevel.DoesNotExist:
            raise NotFoundError("No such hierarchy level.")
        if level.category_id != int(policy_pk):
            raise NotFoundError("No such hierarchy level.")
        for field, value in payload.validated_data.items():
            setattr(level, field, value)
        level.save()
        return Response(s.HierarchyLevelSerializer(level).data)


# -- holiday / RH calendar ---------------------------------------------------

class HolidayCalendarListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_CALENDAR)]

    @extend_schema(responses=s.HolidayCalendarSerializer(many=True))
    def get(self, request):
        return Response(list(HolidayCalendar.objects.all().values()))

    @extend_schema(request=s.HolidayCalendarWriteSerializer, responses=s.HolidayCalendarSerializer)
    def post(self, request):
        payload = s.HolidayCalendarWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        calendar = HolidayCalendar.objects.create(**payload.validated_data)
        return Response(s.HolidayCalendarSerializer(calendar).data, status=status.HTTP_201_CREATED)


class HolidayCalendarDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_CALENDAR)]

    @extend_schema(responses=s.HolidayCalendarSerializer)
    def get(self, request, pk):
        try:
            calendar = HolidayCalendar.objects.get(pk=pk)
        except HolidayCalendar.DoesNotExist:
            raise NotFoundError("No such calendar.")
        return Response(s.HolidayCalendarSerializer(calendar).data)

    @extend_schema(request=s.HolidayCalendarWriteSerializer, responses=s.HolidayCalendarSerializer)
    def put(self, request, pk):
        payload = s.HolidayCalendarWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            calendar = HolidayCalendar.objects.get(pk=pk)
        except HolidayCalendar.DoesNotExist:
            raise NotFoundError("No such calendar.")
        for field, value in payload.validated_data.items():
            setattr(calendar, field, value)
        calendar.save()
        return Response(s.HolidayCalendarSerializer(calendar).data)


class HolidayEntryListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_CALENDAR)]

    @extend_schema(responses=s.HolidayEntrySerializer(many=True))
    def get(self, request, calendar_pk):
        try:
            calendar = HolidayCalendar.objects.get(pk=calendar_pk)
        except HolidayCalendar.DoesNotExist:
            raise NotFoundError("No such calendar.")
        return Response(list(calendar.entries.values()))

    @extend_schema(request=s.HolidayEntryWriteSerializer, responses=s.HolidayEntrySerializer)
    def post(self, request, calendar_pk):
        payload = s.HolidayEntryWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            calendar = HolidayCalendar.objects.get(pk=calendar_pk)
        except HolidayCalendar.DoesNotExist:
            raise NotFoundError("No such calendar.")
        payload.validated_data["calendar"] = calendar
        entry = HolidayEntry.objects.create(**payload.validated_data)
        return Response(s.HolidayEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class HolidayEntryDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_CALENDAR)]

    @extend_schema(responses=s.HolidayEntrySerializer)
    def get(self, request, calendar_pk, entry_pk):
        try:
            entry = HolidayEntry.objects.select_related("calendar").get(pk=entry_pk)
        except HolidayEntry.DoesNotExist:
            raise NotFoundError("No such holiday entry.")
        if entry.calendar_id != int(calendar_pk):
            raise NotFoundError("No such holiday entry.")
        return Response(s.HolidayEntrySerializer(entry).data)

    @extend_schema(request=s.HolidayEntryWriteSerializer, responses=s.HolidayEntrySerializer)
    def put(self, request, calendar_pk, entry_pk):
        payload = s.HolidayEntryWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            entry = HolidayEntry.objects.get(pk=entry_pk)
        except HolidayEntry.DoesNotExist:
            raise NotFoundError("No such holiday entry.")
        if entry.calendar_id != int(calendar_pk):
            raise NotFoundError("No such holiday entry.")
        for field, value in payload.validated_data.items():
            setattr(entry, field, value)
        entry.save()
        return Response(s.HolidayEntrySerializer(entry).data)


class VacationPeriodListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_VACATION)]

    @extend_schema(responses=s.VacationPeriodSerializer(many=True))
    def get(self, request):
        return Response(list(VacationPeriod.objects.all().values()))

    @extend_schema(request=s.VacationPeriodWriteSerializer, responses=s.VacationPeriodSerializer)
    def post(self, request):
        payload = s.VacationPeriodWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        period = VacationPeriod.objects.create(**payload.validated_data)
        return Response(s.VacationPeriodSerializer(period).data, status=status.HTTP_201_CREATED)


class VacationPeriodDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_VACATION)]

    @extend_schema(responses=s.VacationPeriodSerializer)
    def get(self, request, pk):
        try:
            period = VacationPeriod.objects.get(pk=pk)
        except VacationPeriod.DoesNotExist:
            raise NotFoundError("No such vacation period.")
        return Response(s.VacationPeriodSerializer(period).data)

    @extend_schema(request=s.VacationPeriodWriteSerializer, responses=s.VacationPeriodSerializer)
    def put(self, request, pk):
        payload = s.VacationPeriodWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            period = VacationPeriod.objects.get(pk=pk)
        except VacationPeriod.DoesNotExist:
            raise NotFoundError("No such vacation period.")
        for field, value in payload.validated_data.items():
            setattr(period, field, value)
        period.save()
        return Response(s.VacationPeriodSerializer(period).data)


# -- leave requests ----------------------------------------------------------

class LeaveApplicationListView(APIView):
    permission_classes = [MODULE, ScopedCollection(P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        queryset = scoping.leave_applications_for(actor)
        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return Response(list(queryset.values()))

    @extend_schema(request=s.SubmitLeaveSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request):
        payload = s.SubmitLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.create(
            applicant_id=actor.user_id,
            category=payload.validated_data["category"],
            reason=payload.validated_data.get("reason", ""),
            requested_start=payload.validated_data["requested_start"],
            requested_end=payload.validated_data["requested_end"],
            station_leave=payload.validated_data.get("station_leave", False),
            station_leave_note=payload.validated_data.get("station_leave_note", ""),
            substitution_required=payload.validated_data.get("substitution_required", False),
            substitute_applicant_id=payload.validated_data.get("substitute_applicant_id"),
            status="submitted",
        )
        return Response(s.LeaveApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    permission_classes = [MODULE, ScopedCollection(P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationSerializer)
    def get(self, request, pk):
        actor = _actor(request)
        application = scoping.leave_applications_for(actor).filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        return Response(s.LeaveApplicationSerializer(application).data)


class SubmitSubstituteConsentView(APIView):
    permission_classes = [MODULE]

    @extend_schema(request=s.SubstituteConsentSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.SubstituteConsentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        if application.substitute_applicant_id != actor.user_id:
            raise PermissionError("Only the nominated substitute can consent.")
        # Consent releases the gate; the routing decision is recorded by the
        # service which then advances the request to unit head review.
        return Response(s.LeaveApplicationSerializer(application).data)


class DecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        # The service performs the remaining routing and records the decision.
        application.decision = payload.validated_data["decision"]
        application.approval_note = payload.validated_data.get("rationale", "")
        application.save()
        return Response(s.LeaveApplicationSerializer(application).data)


class WithdrawPendingView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.WithdrawPendingSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.WithdrawPendingSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        if application.status == "approved":
            return Response(
                {"detail": "Withdrawal is unavailable after final approval."},
                status=status.HTTP_409_CONFLICT,
            )
        # The service performs the immediate withdrawal with transactional cleanup.
        application.status = "withdrawn"
        application.save()
        return Response(s.LeaveApplicationSerializer(application).data)


class RequestCancellationView(APIView):
    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    @extend_schema(request=s.ApproveCancellationSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.ApproveCancellationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        if application.status != "approved":
            return Response(
                {"detail": "Cancellation is only available for approved leave."},
                status=status.HTTP_409_CONFLICT,
            )
        # Cancellation follows the same applicable hierarchy as the original
        # leave; the service creates a cancel request without editing the
        # approved leave in place.
        application.status = "cancelled"
        application.save()
        return Response(s.LeaveApplicationSerializer(application).data)


class ExtensionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]

    @extend_schema(request=s.ExtensionApplySerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.ExtensionApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        if application.category not in ("EL", "COL", "VL"):
            return Response(
                {"detail": "Extensions are only available for EL, COL and VL."},
                status=status.HTTP_409_CONFLICT,
            )
        # The service validates eligibility, balance, substitute and the
        # applicable hierarchy, then posts only the incremental additional period.
        application.status = "submitted"
        application.save()
        return Response(s.LeaveApplicationSerializer(application).data)


class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]

    @extend_schema(request=s.ResumptionSubmissionSerializer, responses=s.ResumptionSerializer)
    def post(self, request, pk):
        payload = s.ResumptionSubmissionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        application = LeaveApplication.objects.filter(pk=pk).first()
        if application is None:
            raise NotFoundError("No such leave application.")
        if application.category not in ("EL", "COL", "VL"):
            return Response(
                {"detail": "Resumption is not applicable for this leave category."},
                status=status.HTTP_409_CONFLICT,
            )
        if application.resumption_id:
            resumption = application.resumption
            resumption.actual_date = payload.validated_data["actual_date"]
            resumption.early = payload.validated_data.get("early", False)
            resumption.late = payload.validated_data.get("late", False)
            resumption.save()
        else:
            Resumption.objects.create(
                leave_application=application,
                actual_date=payload.validated_data["actual_date"],
                early=payload.validated_data.get("early", False),
                late=payload.validated_data.get("late", False),
            )
        return Response(s.ResumptionSerializer(application.resumption).data)


# -- balance & offline sync --------------------------------------------------

class LeaveBalanceDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_BALANCE)]

    @extend_schema(responses=s.LeaveBalanceSerializer)
    def get(self, request, pk):
        try:
            balance = LeaveBalance.objects.get(pk=pk)
        except LeaveBalance.DoesNotExist:
            raise NotFoundError("No such leave balance.")
        return Response(s.LeaveBalanceSerializer(balance).data)

    @extend_schema(request=s.LeaveBalanceSerializer, responses=s.LeaveBalanceSerializer)
    def put(self, request, pk):
        payload = s.LeaveBalanceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            balance = LeaveBalance.objects.get(pk=pk)
        except LeaveBalance.DoesNotExist:
            raise NotFoundError("No such leave balance.")
        for field, value in payload.validated_data.items():
            setattr(balance, field, value)
        balance.save()
        return Response(s.LeaveBalanceSerializer(balance).data)


class OfflineLeaveEntryView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_OFFLINE)]

    @extend_schema(request=s.LeaveApplicationWriteSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request):
        payload = s.LeaveApplicationWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        # Record already-sanctioned offline leave as a record synchronisation:
        # no second approval workflow is created.
        application = LeaveApplication.objects.create(
            applicant_id=actor.user_id,
            category=payload.validated_data["category"],
            reason=payload.validated_data.get("reason", ""),
            requested_start=payload.validated_data["requested_start"],
            requested_end=payload.validated_data["requested_end"],
            station_leave=payload.validated_data.get("station_leave", False),
            station_leave_note=payload.validated_data.get("station_leave_note", ""),
            substitution_required=payload.validated_data.get("substitution_required", False),
            substitute_applicant_id=payload.validated_data.get("substitute_applicant_id"),
            status="approved",
            decision="approved",
            approved_start=payload.validated_data["requested_start"],
            approved_end=payload.validated_data["requested_end"],
            approved_balance_deducted=0,
        )
        return Response(s.LeaveApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


# -- roles -------------------------------------------------------------------

class RoleListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_ROLE)]

    @extend_schema(responses=s.ELMRoleSerializer(many=True))
    def get(self, request):
        return Response(list(ELMRole.objects.all().values()))

    @extend_schema(request=s.ELMRoleSerializer, responses=s.ELMRoleSerializer)
    def post(self, request):
        payload = s.ELMRoleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        role = ELMRole.objects.create(**payload.validated_data)
        return Response(s.ELMRoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleGrantListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_ROLE)]

    @extend_schema(responses=s.RoleGrantSerializer(many=True))
    def get(self, request):
        return Response(list(RoleGrant.objects.all().values()))

    @extend_schema(request=s.RoleGrantWriteSerializer, responses=s.RoleGrantSerializer)
    def post(self, request):
        payload = s.RoleGrantWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        grant = RoleGrant.objects.create(**payload.validated_data)
        return Response(s.RoleGrantSerializer(grant).data, status=status.HTTP_201_CREATED)


class RoleGrantDeleteView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_ROLE)]

    @extend_schema(responses=s.RoleGrantSerializer)
    def delete(self, request, pk):
        try:
            grant = RoleGrant.objects.get(pk=pk)
        except RoleGrant.DoesNotExist:
            raise NotFoundError("No such role grant.")
        grant.delete()
        return Response({"detail": "Role grant removed."})


# -- SLA ---------------------------------------------------------------------

class SLAConfigurationListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_SLA)]

    @extend_schema(responses=s.SLAConfigurationSerializer(many=True))
    def get(self, request):
        return Response(list(SLAConfiguration.objects.all().values()))

    @extend_schema(request=s.SLAConfigurationWriteSerializer, responses=s.SLAConfigurationSerializer)
    def post(self, request):
        payload = s.SLAConfigurationWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        config = SLAConfiguration.objects.create(**payload.validated_data)
        return Response(s.SLAConfigurationSerializer(config).data, status=status.HTTP_201_CREATED)


class SLAConfigurationDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_SLA)]

    @extend_schema(responses=s.SLAConfigurationSerializer)
    def get(self, request, pk):
        try:
            config = SLAConfiguration.objects.get(pk=pk)
        except SLAConfiguration.DoesNotExist:
            raise NotFoundError("No such SLA configuration.")
        return Response(s.SLAConfigurationSerializer(config).data)

    @extend_schema(request=s.SLAConfigurationWriteSerializer, responses=s.SLAConfigurationSerializer)
    def put(self, request, pk):
        payload = s.SLAConfigurationWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            config = SLAConfiguration.objects.get(pk=pk)
        except SLAConfiguration.DoesNotExist:
            raise NotFoundError("No such SLA configuration.")
        for field, value in payload.validated_data.items():
            setattr(config, field, value)
        config.save()
        return Response(s.SLAConfigurationSerializer(config).data)
