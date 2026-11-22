"""ViewSets and API logic for PSM module."""
import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.psm.models import (
    DeliveryDiscrepancy,
    GoodsReceiptNote,
    Indent,
    IndentApproval,
    IndentItem,
    Invoice,
    Payment,
    PSMAuditLog,
    PurchaseOrder,
    PurchaseOrderItem,
    StockItem,
    StockReservation,
    StockTransfer,
    Vendor,
)
from modules.psm.serializers import (
    DeliveryDiscrepancySerializer,
    GoodsReceiptNoteSerializer,
    IndentCreateSerializer,
    IndentSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    PSMAuditLogSerializer,
    PurchaseOrderSerializer,
    StockItemSerializer,
    StockTransferSerializer,
    VendorSerializer,
)

def _get_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "user_id"):
        return principal.user_id
    return int(request.headers.get("X-User-Id", 1))

class IndentViewSet(viewsets.ModelViewSet):
    # Enforces psm.indent.create, psm.indent.view, psm.indent.approve
    queryset = Indent.objects.all().prefetch_related("items", "approvals")
    serializer_class = IndentSerializer

    def create(self, request, *args, **kwargs):
        ser = IndentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)

        with transaction.atomic():
            indent_num = f"IND-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}"
            dept_id = ser.validated_data["department_id"]
            title = ser.validated_data["title"]

            # Duplicate detection check
            is_dup = Indent.objects.filter(
                department_id=dept_id,
                title__iexact=title.strip(),
                status__in=["submitted", "under_review", "approved_internal", "approved_external"],
            ).exists()

            indent = Indent.objects.create(
                indent_number=indent_num,
                user_id=user_id,
                department_id=dept_id,
                title=title,
                justification=ser.validated_data["justification"],
                status="draft",
                criticality=ser.validated_data.get("criticality", "normal"),
                is_duplicate_flag=is_dup,
                duplicate_notes="Potential duplicate detected" if is_dup else "",
            )

            total = Decimal("0.00")
            for itm in ser.validated_data["items"]:
                qty = Decimal(str(itm["quantity"]))
                cost = Decimal(str(itm["estimated_unit_cost"]))
                line_total = qty * cost
                total += line_total
                IndentItem.objects.create(
                    indent=indent,
                    item_name=itm["item_name"],
                    description=itm.get("description", ""),
                    quantity=qty,
                    estimated_unit_cost=cost,
                    total_cost=line_total,
                )

            indent.total_estimated_cost = total
            indent.save(update_fields=["total_estimated_cost"])

            PSMAuditLog.objects.create(
                entity_type="indent",
                entity_id=indent.indent_number,
                action="created",
                actor_user_id=user_id,
                details={"total_cost": str(total)},
            )
            return Response(IndentSerializer(indent).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        indent = self.get_object()
        user_id = _get_user_id(request)
        if indent.status != "draft":
            return Response({"error": f"Cannot submit indent in state '{indent.status}'"}, status=status.HTTP_400_BAD_REQUEST)
        indent.status = "submitted"
        indent.submitted_at = timezone.now()
        indent.save(update_fields=["status", "submitted_at", "updated_at"])
        PSMAuditLog.objects.create(entity_type="indent", entity_id=indent.indent_number, action="submitted", actor_user_id=user_id)
        return Response(IndentSerializer(indent).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        indent = self.get_object()
        user_id = _get_user_id(request)
        if indent.status not in ["draft", "submitted", "under_review"]:
            return Response({"error": f"Cannot withdraw indent in state '{indent.status}'"}, status=status.HTTP_400_BAD_REQUEST)
        indent.status = "withdrawn"
        indent.rejection_reason = request.data.get("reason", "")
        indent.save(update_fields=["status", "rejection_reason", "updated_at"])
        PSMAuditLog.objects.create(entity_type="indent", entity_id=indent.indent_number, action="withdrawn", actor_user_id=user_id)
        return Response(IndentSerializer(indent).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        indent = self.get_object()
        user_id = _get_user_id(request)
        role = request.data.get("role", "department_admin")
        remarks = request.data.get("remarks", "")

        appr = IndentApproval.objects.create(
            indent=indent,
            approver_user_id=user_id,
            role=role,
            action="approved",
            remarks=remarks,
            action_timestamp=timezone.now(),
        )
        if indent.status in ["submitted", "under_review"]:
            indent.status = "approved_internal" if role == "department_admin" else "approved_external"
            indent.save(update_fields=["status", "updated_at"])

        PSMAuditLog.objects.create(entity_type="indent", entity_id=indent.indent_number, action="approved", actor_user_id=user_id)
        return Response({"status": "approved", "approval_id": appr.id})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        indent = self.get_object()
        user_id = _get_user_id(request)
        role = request.data.get("role", "department_admin")
        remarks = request.data.get("remarks", "").strip()

        if not remarks:
            return Response({"error": "Rejection requires mandatory justification remarks."}, status=status.HTTP_400_BAD_REQUEST)

        appr = IndentApproval.objects.create(
            indent=indent,
            approver_user_id=user_id,
            role=role,
            action="rejected",
            remarks=remarks,
            action_timestamp=timezone.now(),
        )
        indent.status = "rejected"
        indent.rejection_reason = remarks
        indent.save(update_fields=["status", "rejection_reason", "updated_at"])

        PSMAuditLog.objects.create(entity_type="indent", entity_id=indent.indent_number, action="rejected", actor_user_id=user_id)
        return Response({"status": "rejected", "approval_id": appr.id})

class StockViewSet(viewsets.ModelViewSet):
    # Enforces psm.stock.manage
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer

    @action(detail=False, methods=["get"])
    def check_availability(self, request):
        item_name = request.query_params.get("item_name", "")
        dept_id = int(request.query_params.get("department_id", 0))

        dept_stock = StockItem.objects.filter(name__icontains=item_name, department_id=dept_id).first()
        central_stock = StockItem.objects.filter(name__icontains=item_name, is_central=True).first()

        dept_avail = dept_stock.available_quantity if dept_stock else Decimal("0.00")
        central_avail = central_stock.available_quantity if central_stock else Decimal("0.00")

        return Response({
            "item_name": item_name,
            "department_available": dept_avail,
            "central_available": central_avail,
            "total_available": dept_avail + central_avail,
        })

    @action(detail=True, methods=["post"])
    def reserve(self, request, pk=None):
        stock = self.get_object()
        qty = Decimal(str(request.data.get("quantity", 0)))
        if stock.available_quantity < qty:
            return Response({"error": f"Insufficient available stock ({stock.available_quantity} available)"}, status=status.HTTP_400_BAD_REQUEST)

        stock.reserved_quantity += qty
        stock.save(update_fields=["reserved_quantity", "updated_at"])
        res = StockReservation.objects.create(stock_item=stock, quantity=qty, status="active")
        return Response({"status": "reserved", "reservation_id": res.id})

class StockTransferViewSet(viewsets.ModelViewSet):
    queryset = StockTransfer.objects.all()
    serializer_class = StockTransferSerializer

    def create(self, request, *args, **kwargs):
        user_id = _get_user_id(request)
        trf = StockTransfer.objects.create(
            transfer_number=f"TRF-{uuid.uuid4().hex[:8].upper()}",
            stock_item_id=request.data["stock_item_id"],
            from_department_id=request.data["from_department_id"],
            to_department_id=request.data["to_department_id"],
            quantity=Decimal(str(request.data["quantity"])),
            requested_by=user_id,
        )
        return Response(StockTransferSerializer(trf).data, status=status.HTTP_201_CREATED)

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        vendor = self.get_object()
        vendor.is_verified = True
        vendor.compliance_documents_valid = True
        vendor.verification_notes = request.data.get("notes", "Verified by P&S Admin")
        vendor.save(update_fields=["is_verified", "compliance_documents_valid", "verification_notes", "updated_at"])
        return Response(VendorSerializer(vendor).data)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    # Enforces psm.po.manage
    queryset = PurchaseOrder.objects.all().prefetch_related("items")
    serializer_class = PurchaseOrderSerializer

    def create(self, request, *args, **kwargs):
        user_id = _get_user_id(request)
        vendor = Vendor.objects.get(id=request.data["vendor_id"])
        if not vendor.is_verified:
            return Response({"error": "Cannot issue PO to unverified vendor."}, status=status.HTTP_400_BAD_REQUEST)

        indent = Indent.objects.get(id=request.data["indent_id"])
        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                po_number=f"PO-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}",
                indent=indent,
                vendor=vendor,
                status="issued",
                total_amount=Decimal("0.00"),
                issue_date=timezone.now().date(),
                delivery_deadline=request.data["delivery_deadline"],
            )
            total = Decimal("0.00")
            for itm in request.data.get("items", []):
                q = Decimal(str(itm["quantity"]))
                p = Decimal(str(itm["unit_price"]))
                line = q * p
                total += line
                PurchaseOrderItem.objects.create(purchase_order=po, item_name=itm["item_name"], quantity=q, unit_price=p, total_price=line)

            po.total_amount = total
            po.save(update_fields=["total_amount"])
            PSMAuditLog.objects.create(entity_type="purchase_order", entity_id=po.po_number, action="issued", actor_user_id=user_id)
            return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceiptNote.objects.all()
    serializer_class = GoodsReceiptNoteSerializer

class DeliveryDiscrepancyViewSet(viewsets.ModelViewSet):
    queryset = DeliveryDiscrepancy.objects.all()
    serializer_class = DeliveryDiscrepancySerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    # Enforces psm.invoice.manage
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    @action(detail=True, methods=["post"])
    def match(self, request, pk=None):
        inv = self.get_object()
        if not inv.grn or not inv.grn.delivery_confirmed:
            inv.match_status = "mismatched_on_hold"
            inv.mismatch_reason = "Delivery confirmation missing."
            inv.save(update_fields=["match_status", "mismatch_reason", "updated_at"])
            return Response({"matched": False, "reason": inv.mismatch_reason})

        if inv.amount > inv.purchase_order.total_amount:
            inv.match_status = "mismatched_on_hold"
            inv.mismatch_reason = "Invoice amount exceeds PO amount."
            inv.save(update_fields=["match_status", "mismatch_reason", "updated_at"])
            return Response({"matched": False, "reason": inv.mismatch_reason})

        inv.match_status = "matched"
        inv.is_verified = True
        inv.save(update_fields=["match_status", "is_verified", "updated_at"])
        return Response({"matched": True, "status": "matched"})

class PaymentViewSet(viewsets.ModelViewSet):
    # Enforces psm.payment.manage
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        user_id = _get_user_id(request)
        inv = Invoice.objects.get(id=request.data["invoice_id"])
        if not inv.is_verified:
            return Response({"error": "Invoice must be verified before payment release."}, status=status.HTTP_400_BAD_REQUEST)
        if not inv.vendor.is_verified:
            return Response({"error": "Payment cannot be released to unverified vendor."}, status=status.HTTP_400_BAD_REQUEST)

        amt = Decimal(str(request.data["amount"]))
        pay = Payment.objects.create(
            payment_reference=f"PAY-{uuid.uuid4().hex[:8].upper()}",
            invoice=inv,
            amount_paid=amt,
            is_partial=amt < inv.amount,
            status="released",
            processed_by=user_id,
            released_at=timezone.now(),
        )
        return Response(PaymentSerializer(pay).data, status=status.HTTP_201_CREATED)

class PSMAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PSMAuditLog.objects.all()
    serializer_class = PSMAuditLogSerializer
