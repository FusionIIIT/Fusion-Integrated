from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from modules.iwd.models import Request, WorkOrder, Vendor, Bill, BillItem, Budget, Proposal, ProposalItem, InventoryItem, InventoryTransaction, Feedback, SLAEscalation
from modules.iwd.serializers import RequestSerializer, WorkOrderSerializer, VendorSerializer, BillSerializer, BillItemSerializer, BudgetSerializer, ProposalSerializer, ProposalItemSerializer, InventoryItemSerializer, InventoryTransactionSerializer, FeedbackSerializer, SLAEscalationSerializer

from fusion_auth.permissions import HasModuleGrant


class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [HasModuleGrant('iwd')]

    @action(detail=True, methods=['post'])
    def admin_approval(self, request, pk=None):
        obj = self.get_object()
        if obj.status != 'Pending':
            return Response({'detail': 'Only Pending requests can be approved by admin.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = 'Admin Approved'
        obj.save()
        return Response({'status': obj.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def hod_approval(self, request, pk=None):
        obj = self.get_object()
        if obj.status != 'Admin Approved':
            return Response({'detail': 'Only Admin Approved requests can be approved by HOD/Dean.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = 'HOD/Dean Approved'
        obj.save()
        return Response({'status': obj.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def director_approval(self, request, pk=None):
        obj = self.get_object()
        if obj.status != 'HOD/Dean Approved':
            return Response({'detail': 'Only HOD/Dean Approved requests can be approved by director.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = 'Approved'
        obj.save()
        return Response({'status': obj.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        obj = self.get_object()
        if obj.status == 'Approved':
            return Response({'detail': 'Approved requests cannot be rejected.'},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.status = 'Rejected'
        obj.save()
        return Response({'status': obj.status}, status=status.HTTP_200_OK)

class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    permission_classes = [HasModuleGrant('iwd')]

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [HasModuleGrant('iwd')]

class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [HasModuleGrant('iwd')]

class BillItemViewSet(viewsets.ModelViewSet):
    queryset = BillItem.objects.all()
    serializer_class = BillItemSerializer
    permission_classes = [HasModuleGrant('iwd')]

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [HasModuleGrant('iwd')]

class ProposalViewSet(viewsets.ModelViewSet):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer
    permission_classes = [HasModuleGrant('iwd')]

class ProposalItemViewSet(viewsets.ModelViewSet):
    queryset = ProposalItem.objects.all()
    serializer_class = ProposalItemSerializer
    permission_classes = [HasModuleGrant('iwd')]

class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [HasModuleGrant('iwd')]

class InventoryTransactionViewSet(viewsets.ModelViewSet):
    queryset = InventoryTransaction.objects.all()
    serializer_class = InventoryTransactionSerializer
    permission_classes = [HasModuleGrant('iwd')]

class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [HasModuleGrant('iwd')]

class SLAEscalationViewSet(viewsets.ModelViewSet):
    queryset = SLAEscalation.objects.all()
    serializer_class = SLAEscalationSerializer
    permission_classes = [HasModuleGrant('iwd')]

