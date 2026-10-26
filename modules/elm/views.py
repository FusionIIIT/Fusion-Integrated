from rest_framework import generics
from fusion_auth.permissions import HasModuleGrant, HasPermission

from .models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    LeaveSubstitute,
    LeaveApproval,
    LeaveCalendarPeriod,
)
from .serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveApplicationSerializer,
    LeaveSubstituteSerializer,
    LeaveApprovalSerializer,
    LeaveCalendarPeriodSerializer,
)

MODULE = HasModuleGrant("elm")


def actor_id(request):
    principal = getattr(request, "principal", None)
    return principal.user_id if principal is not None else None


class LeaveTypeListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.application.create")]
    serializer_class = LeaveTypeSerializer
    queryset = LeaveType.objects.filter(is_active=True)


class LeaveBalanceListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.balance.view_self")]
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        return LeaveBalance.objects.filter(user_id=actor_id(self.request))


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            checks = [MODULE(), HasPermission("elm.application.create")()]
        else:
            checks = [MODULE(), HasPermission("elm.application.view_self")()]
        return checks

    def get_queryset(self):
        return LeaveApplication.objects.filter(user_id=actor_id(self.request))

    def perform_create(self, serializer):
        serializer.save(user_id=actor_id(self.request))


class LeaveApplicationDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [MODULE, HasPermission("elm.application.view_self")]
    serializer_class = LeaveApplicationSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return LeaveApplication.objects.filter(
            user_id=actor_id(self.request),
            status="draft",
        )


class LeaveSubstituteListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveSubstituteSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            checks = [MODULE(), HasPermission("elm.application.create")()]
        else:
            checks = [MODULE(), HasPermission("elm.substitute.respond")()]
        return checks

    def get_queryset(self):
        uid = actor_id(self.request)
        return LeaveSubstitute.objects.filter(
            substitute_user_id=uid
        ) | LeaveSubstitute.objects.filter(user_id=uid)

    def perform_create(self, serializer):
        serializer.save(user_id=actor_id(self.request))


class LeaveApprovalListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(
        "elm.application.approve",
        "elm.application.recommend",
    )]
    serializer_class = LeaveApprovalSerializer

    def get_queryset(self):
        return LeaveApproval.objects.filter(
            approver_user_id=actor_id(self.request)
        )


# Management endpoints: permissions are enforced at the HTTP boundary.
class EmployeeLeaveApplicationsView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.application.view")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        return LeaveApplication.objects.all()


class LeaveBalanceManagementView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.balance.manage")]
    serializer_class = LeaveBalanceSerializer
    queryset = LeaveBalance.objects.all()


class LeavePolicyManagementView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.policy.manage")]
    serializer_class = LeaveTypeSerializer
    queryset = LeaveType.objects.all()


class LeaveCalendarManagementView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission("elm.calendar.manage")]
    serializer_class = LeaveCalendarPeriodSerializer
    queryset = LeaveCalendarPeriod.objects.all()

class OfflineLeaveRecordingView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission("elm.leave.record_offline")]
    serializer_class = LeaveApplicationSerializer
    queryset = LeaveApplication.objects.none()


class YearEndLeaveProcessingView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.leave.process_year_end")]
    serializer_class = LeaveBalanceSerializer
    queryset = LeaveBalance.objects.none()


class LeaveWithdrawalView(generics.UpdateAPIView):
    permission_classes = [MODULE, HasPermission("elm.application.withdraw")]
    serializer_class = LeaveApplicationSerializer
    http_method_names = ["patch", "head", "options"]

    def get_queryset(self):
        return LeaveApplication.objects.filter(
            user_id=actor_id(self.request),
            status="pending",
        )

    def perform_update(self, serializer):
        serializer.save(status="withdrawn")
