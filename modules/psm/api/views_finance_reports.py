# Invoices, payments, dashboard, reports, schedules, audit trail, notifications, and policy views.
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.psm.api import serializers as ser
from modules.psm.selectors import dashboard as dash_sel
from modules.psm.selectors import scoping
from modules.psm.services import finance, policy, reports


def _paginate(request, qs, serializer_cls):
    paginator = CursorPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


class DashboardView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.dashboard.view")]

    @extend_schema(
        tags=["psm"],
        summary="View real-time scoped PSM dashboard (PSM-UC-030)",
        responses={200: ser.DashboardSerializer},
    )
    def get(self, request):
        return Response(dash_sel.dashboard_summary(request.principal))


class InvoiceListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.invoice.view" if self.request.method == "GET" else "psm.invoice.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List vendor invoices (PSM-UC-013)",
        responses={200: ser.InvoiceReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(
            request, scoping.invoices_for(request.principal), ser.InvoiceReadSerializer
        )

    @extend_schema(
        tags=["psm"],
        summary="Record a vendor invoice against a PO (PSM-UC-013)",
        request=ser.InvoiceCreateSerializer,
        responses={201: ser.InvoiceReadSerializer},
    )
    def post(self, request):
        s = ser.InvoiceCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = finance.submit_invoice(actor=request.principal, **s.validated_data)
        return Response(ser.InvoiceReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class InvoiceVerifyView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.invoice.review")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Three-way match and verify an invoice (PSM-UC-013)",
        request=None,
        responses={200: ser.InvoiceReadSerializer},
    )
    def post(self, request, invoice_id: int):
        obj = finance.verify_invoice(actor=request.principal, invoice_id=invoice_id)
        return Response(ser.InvoiceReadSerializer(obj).data)


class InvoiceHoldView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.invoice.review")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Place an invoice on hold with reason (PSM-UC-029)",
        request=ser.ReasonSerializer,
        responses={200: ser.InvoiceReadSerializer},
    )
    def post(self, request, invoice_id: int):
        s = ser.ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = finance.hold_invoice(
            actor=request.principal, invoice_id=invoice_id, reason=s.validated_data["reason"]
        )
        return Response(ser.InvoiceReadSerializer(obj).data)


class InvoicePayView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.payment.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Release full or partial vendor payment (PSM-UC-029)",
        request=ser.PaymentCreateSerializer,
        responses={201: ser.PaymentReadSerializer},
    )
    def post(self, request, invoice_id: int):
        s = ser.PaymentCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tx = finance.process_payment(
            actor=request.principal, invoice_id=invoice_id, **s.validated_data
        )
        return Response(ser.PaymentReadSerializer(tx).data, status=status.HTTP_201_CREATED)


class ReportGenerateView(APIView):
    permission_classes = [
        HasModuleGrant("psm"),
        HasPermission("psm.report.view", "psm.financial_report.view"),
    ]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Generate operational, procurement, stock, or financial report (PSM-UC-010, 015)",
        request=ser.ReportGenerateSerializer,
        responses={200: dict},
    )
    def post(self, request):
        s = ser.ReportGenerateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = reports.generate_report(actor=request.principal, **s.validated_data)
        return Response(result)


class ReportExportView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.report.export")]
    throttle_scope = "psm_export"

    @extend_schema(
        tags=["psm"],
        summary="Export a formula-safe CSV report (AFR-PSM-079)",
        request=ser.ReportGenerateSerializer,
        responses={200: str},
    )
    def post(self, request):
        s = ser.ReportGenerateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        filename, body = reports.export_report_csv(actor=request.principal, **s.validated_data)
        resp = HttpResponse(body, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp["X-Content-Type-Options"] = "nosniff"
        return resp


class ReportScheduleListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.report.view" if self.request.method == "GET" else "psm.report.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List scoped report schedules (PSM-UC-031)",
        responses={200: ser.ReportScheduleReadSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(
            request,
            scoping.report_schedules_for(request.principal),
            ser.ReportScheduleReadSerializer,
        )

    @extend_schema(
        tags=["psm"],
        summary="Create a scheduled report definition (PSM-UC-031)",
        request=ser.ReportScheduleCreateSerializer,
        responses={201: ser.ReportScheduleReadSerializer},
    )
    def post(self, request):
        s = ser.ReportScheduleCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = reports.create_schedule(actor=request.principal, **s.validated_data)
        return Response(ser.ReportScheduleReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class ReportScheduleUpdateView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.report.create")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Update or disable a report schedule (PSM-UC-031)",
        request=ser.ReportSchedulePatchSerializer,
        responses={200: ser.ReportScheduleReadSerializer},
    )
    def patch(self, request, schedule_id: int):
        s = ser.ReportSchedulePatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = reports.update_schedule(
            actor=request.principal, schedule_id=schedule_id, **s.validated_data
        )
        return Response(ser.ReportScheduleReadSerializer(obj).data)


class AuditLogListView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.audit.view")]

    @extend_schema(
        tags=["psm"],
        summary="Audit procurement and financial records (PSM-UC-014)",
        responses={200: ser.AuditLogSerializer(many=True)},
    )
    def get(self, request):
        qs = scoping.audit_logs_for(request.principal)
        target_type = (request.query_params.get("target_type") or "").strip()
        if target_type:
            qs = qs.filter(target_type=target_type)
        return _paginate(request, qs, ser.AuditLogSerializer)


class NotificationListView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.dashboard.view")]

    @extend_schema(
        tags=["psm"],
        summary="List caller's retained PSM communication history (BR-PSM-006)",
        responses={200: ser.NotificationSerializer(many=True)},
    )
    def get(self, request):
        return _paginate(
            request, scoping.notifications_for(request.principal), ser.NotificationSerializer
        )


class PolicyListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.policy.view" if self.request.method == "GET" else "psm.policy.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List active and historical PSM policy versions (BR-PSM-028)",
        responses={200: ser.PsmPolicySerializer(many=True)},
    )
    def get(self, request):
        rows = scoping.all_policies()[:50]
        return Response({"results": ser.PsmPolicySerializer(rows, many=True).data})

    @extend_schema(
        tags=["psm"],
        summary="Publish a new effective-dated PSM policy version (BR-PSM-028)",
        request=ser.PsmPolicySerializer,
        responses={201: ser.PsmPolicySerializer},
    )
    def post(self, request):
        s = ser.PsmPolicySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = policy.publish_policy(actor=request.principal, **s.validated_data)
        return Response(ser.PsmPolicySerializer(obj).data, status=status.HTTP_201_CREATED)
