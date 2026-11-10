from rest_framework import serializers

from .notifications import NotificationSerializer
from .patients import (
    PatientVisitSerializer,
    PrescriptionSerializer,
    PrescriptionCreateSerializer,
)
from .claims import (
    ReimbursementClaimSerializer,
    ClaimActionSerializer,
    ClaimDecisionSerializer,
    ReimbursementPaymentSerializer,
)
from .inventory import (
    InventoryItemSerializer,
    StockAdjustmentSerializer,
    RequisitionSerializer,
    RequisitionCreateSerializer,
    RequisitionDecisionSerializer,
)
