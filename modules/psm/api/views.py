from rest_framework import viewsets
from fusion_auth.permissions import HasModuleGrant
from modules.psm.models import StockItem, PurchaseIndent, IndentItem
from modules.psm.serializers import StockItemSerializer, PurchaseIndentSerializer, IndentItemSerializer

MODULE = HasModuleGrant("psm")

class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.all().order_by("-id")
    serializer_class = StockItemSerializer
    permission_classes = [MODULE]

class PurchaseIndentViewSet(viewsets.ModelViewSet):
    queryset = PurchaseIndent.objects.all().order_by("-id")
    serializer_class = PurchaseIndentSerializer
    permission_classes = [MODULE]

    def perform_create(self, serializer):
        user_id = getattr(getattr(self.request, "principal", None), "user_id", 1001)
        serializer.save(user_id=user_id)

class IndentItemViewSet(viewsets.ModelViewSet):
    queryset = IndentItem.objects.all().order_by("-id")
    serializer_class = IndentItemSerializer
    permission_classes = [MODULE]
