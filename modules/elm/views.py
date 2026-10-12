from rest_framework import viewsets, mixins
from modules.elm.serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveApplicationSerializer, LeaveSubstituteSerializer, LeaveApprovalSerializer
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication, LeaveSubstitute, LeaveApproval

class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

class LeaveApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer

class LeaveSubstituteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = LeaveSubstitute.objects.all()
    serializer_class = LeaveSubstituteSerializer

class LeaveApprovalViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = LeaveApproval.objects.all()
    serializer_class = LeaveApprovalSerializer
