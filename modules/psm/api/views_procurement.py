# Vendors, tenders, purchase orders, GRNs, receipt confirmation, and discrepancy resolution views.
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.psm.api import serializers as ser
from modules.psm.selectors import scoping
from modules.psm.services import discrepancies, procurement, receipts, tenders, vendors


def _paginate(request, qs, serializer_cls):
    paginator = CursorPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


class VendorListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.vendor.view" if self.request.method == "GET" else "psm.vendor.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List vendor master records (PSM-UC-019)",
        responses={200: ser.VendorReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(request, scoping.vendors_for(request.principal), ser.VendorReadSerializer)

    @extend_schema(
        tags=["psm"],
        summary="Onboard a new vendor (PSM-UC-019)",
        request=ser.VendorWriteSerializer,
        responses={201: ser.VendorReadSerializer},
        examples=[
            OpenApiExample(
                "Onboard vendor",
                value={
                    "name": "Apex Labs Pvt Ltd",
                    "gstin": "23AABCU9603R1ZM",
                    "bank_account_number": "123456789012",
                    "bank_ifsc": "SBIN0001234",
                    "bank_name": "SBI",
                    "compliance_documents": ["GST Cert"],
                },
            )
        ],
    )
    def post(self, request):
        s = ser.VendorWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        data.pop("change_reason", None)
        obj = vendors.onboard_vendor(actor=request.principal, **data)
        return Response(ser.VendorReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class VendorDetailView(APIView):
    def get_permissions(self):
        perm = "psm.vendor.view" if self.request.method == "GET" else "psm.vendor.update"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "PATCH":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="Get vendor detail and version history (BR-PSM-025)",
        responses={200: ser.VendorDetailSerializer},
    )
    def get(self, request, vendor_id: int):
        obj = (
            scoping.vendors_for(request.principal)
            .prefetch_related("versions")
            .filter(pk=vendor_id)
            .first()
        )
        if obj is None:
            raise NotFoundError("Vendor not found.")
        return Response(ser.VendorDetailSerializer(obj).data)

    @extend_schema(
        tags=["psm"],
        summary="Update vendor master data and append version (PSM-UC-019)",
        request=ser.VendorPatchSerializer,
        responses={200: ser.VendorReadSerializer},
    )
    def patch(self, request, vendor_id: int):
        s = ser.VendorPatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = vendors.update_vendor(
            actor=request.principal, vendor_id=vendor_id, **s.validated_data
        )
        return Response(ser.VendorReadSerializer(obj).data)


class VendorVerifyView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.vendor.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Validate and verify vendor master data (BR-PSM-012)",
        request=None,
        responses={200: ser.VendorReadSerializer},
    )
    def post(self, request, vendor_id: int):
        obj = vendors.verify_vendor(actor=request.principal, vendor_id=vendor_id)
        return Response(ser.VendorReadSerializer(obj).data)


class TenderListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.tender.view" if self.request.method == "GET" else "psm.tender.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List tenders and bids (PSM-UC-022)",
        responses={200: ser.TenderReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(request, scoping.tenders_for(request.principal), ser.TenderReadSerializer)

    @extend_schema(
        tags=["psm"],
        summary="Create a draft tender (PSM-UC-022)",
        request=ser.TenderCreateSerializer,
        responses={201: ser.TenderReadSerializer},
    )
    def post(self, request):
        s = ser.TenderCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = tenders.create_tender(actor=request.principal, **s.validated_data)
        return Response(ser.TenderReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class TenderPublishView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.tender.publish")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Publish a tender invitation (AFR-PSM-032)",
        request=None,
        responses={200: ser.TenderReadSerializer},
    )
    def post(self, request, tender_id: int):
        obj = tenders.publish_tender(actor=request.principal, tender_id=tender_id)
        return Response(ser.TenderReadSerializer(obj).data)


class TenderBidCreateView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.tender.create")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Record a vendor bid on a published tender (AFR-PSM-033)",
        request=ser.TenderBidCreateSerializer,
        responses={201: ser.TenderBidReadSerializer},
    )
    def post(self, request, tender_id: int):
        s = ser.TenderBidCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = tenders.record_bid(actor=request.principal, tender_id=tender_id, **s.validated_data)
        return Response(ser.TenderBidReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class TenderEvaluateView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.tender.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Record bid evaluation against tender criteria (BR-PSM-023)",
        request=ser.TenderEvaluateSerializer,
        responses={200: ser.TenderReadSerializer},
    )
    def post(self, request, tender_id: int):
        s = ser.TenderEvaluateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = tenders.evaluate_bids(
            actor=request.principal, tender_id=tender_id, **s.validated_data
        )
        return Response(ser.TenderReadSerializer(obj).data)


class TenderAwardView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.tender.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Record committee approval and award tender (BR-PSM-023)",
        request=ser.TenderAwardSerializer,
        responses={200: ser.TenderReadSerializer},
    )
    def post(self, request, tender_id: int):
        s = ser.TenderAwardSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = tenders.award_tender(actor=request.principal, tender_id=tender_id, **s.validated_data)
        return Response(ser.TenderReadSerializer(obj).data)


class PurchaseOrderListCreateView(APIView):
    def get_permissions(self):
        perm = (
            "psm.purchase_order.view"
            if self.request.method == "GET"
            else "psm.purchase_order.create"
        )
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List scoped purchase orders (PSM-UC-027)",
        responses={200: ser.PurchaseOrderReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(
            request, scoping.purchase_orders_for(request.principal), ser.PurchaseOrderReadSerializer
        )

    @extend_schema(
        tags=["psm"],
        summary="Create and issue a purchase order (PSM-UC-026)",
        request=ser.PurchaseOrderCreateSerializer,
        responses={201: ser.PurchaseOrderReadSerializer},
    )
    def post(self, request):
        s = ser.PurchaseOrderCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = procurement.create_and_issue_po(actor=request.principal, **s.validated_data)
        return Response(ser.PurchaseOrderReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class PurchaseOrderUpdateView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.purchase_order.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Update PO status and delivery schedule (PSM-UC-027)",
        request=ser.PurchaseOrderUpdateSerializer,
        responses={200: ser.PurchaseOrderReadSerializer},
    )
    def patch(self, request, po_id: int):
        s = ser.PurchaseOrderUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = procurement.update_po_schedule(
            actor=request.principal, po_id=po_id, **s.validated_data
        )
        return Response(ser.PurchaseOrderReadSerializer(obj).data)


class GrnListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.grn.view" if self.request.method == "GET" else "psm.grn.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List scoped goods receipt notes (PSM-UC-028)",
        responses={200: ser.GrnReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(request, scoping.grns_for(request.principal), ser.GrnReadSerializer)

    @extend_schema(
        tags=["psm"],
        summary="Inspect delivery and record a GRN (PSM-UC-028)",
        request=ser.GrnCreateSerializer,
        responses={201: ser.GrnReadSerializer},
    )
    def post(self, request):
        s = ser.GrnCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = receipts.record_grn(actor=request.principal, **s.validated_data)
        return Response(ser.GrnReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class GrnConfirmView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.grn.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Confirm delivery receipt and post stock (PSM-UC-002)",
        request=None,
        responses={200: ser.GrnReadSerializer},
    )
    def post(self, request, grn_id: int):
        obj = receipts.confirm_receipt(actor=request.principal, grn_id=grn_id)
        return Response(ser.GrnReadSerializer(obj).data)


class DiscrepancyListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.grn.view" if self.request.method == "GET" else "psm.grn.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List scoped delivery discrepancy cases (PSM-UC-020)",
        responses={200: ser.DiscrepancyReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(
            request, scoping.discrepancies_for(request.principal), ser.DiscrepancyReadSerializer
        )

    @extend_schema(
        tags=["psm"],
        summary="Report delivery discrepancy and initiate return/replacement (PSM-UC-020)",
        request=ser.DiscrepancyCreateSerializer,
        responses={201: ser.DiscrepancyReadSerializer},
    )
    def post(self, request):
        s = ser.DiscrepancyCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = discrepancies.report_discrepancy(actor=request.principal, **s.validated_data)
        return Response(ser.DiscrepancyReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class DiscrepancyCommCreateView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.discrepancy.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Log vendor communication on a discrepancy case (PSM-UC-032)",
        request=ser.DiscrepancyCommSerializer,
        responses={201: ser.DiscrepancyCommSerializer},
    )
    def post(self, request, case_id: int):
        s = ser.DiscrepancyCommSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = discrepancies.add_communication(
            actor=request.principal, case_id=case_id, **s.validated_data
        )
        return Response(ser.DiscrepancyCommSerializer(obj).data, status=status.HTTP_201_CREATED)


class DiscrepancyResolveView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.discrepancy.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Resolve a discrepancy via return/adjustment or replacement (PSM-UC-032)",
        request=ser.DiscrepancyResolveSerializer,
        responses={200: ser.DiscrepancyReadSerializer},
    )
    def post(self, request, case_id: int):
        s = ser.DiscrepancyResolveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = discrepancies.resolve_case(
            actor=request.principal, case_id=case_id, **s.validated_data
        )
        return Response(ser.DiscrepancyReadSerializer(obj).data)
