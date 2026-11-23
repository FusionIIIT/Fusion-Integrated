from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.phc.api import serializers as s
from modules.phc.models import (
    DoctorAttendance,
    DoctorScheduleSlot,
)
from modules.phc.selectors import inventory as inventory_selectors
from modules.phc.selectors import scoping
from modules.phc.services import inventory as inventory_service
from modules.phc.services import operations as operations_service
from modules.phc.services import pdf as pdf_service
from modules.phc.services import records as records_service
from modules.phc.services import reimbursements as reimbursement_service
from modules.phc.services import reports as report_service
from modules.phc.services import requisitions as requisition_service
from modules.phc.services import schedules as schedule_service

MODULE_GATE = HasModuleGrant("phc")
P_SCHEDULE_VIEW = "phc.doctor_schedule.view"
P_SCHEDULE_CREATE = "phc.doctor_schedule.create"
P_SCHEDULE_UPDATE = "phc.doctor_schedule.update"
P_SCHEDULE_PUBLISH = "phc.doctor_schedule.publish"
P_ATTENDANCE_UPDATE = "phc.doctor_attendance.update"
P_RECORD_VIEW = "phc.patient_record.view"
P_RECORD_CREATE = "phc.patient_record.create"
P_RECORD_EXPORT = "phc.record.export"
P_CLAIM_VIEW = "phc.reimbursement.view"
P_CLAIM_CREATE = "phc.reimbursement.create"
P_CLAIM_REVIEW = "phc.reimbursement.review"
P_CLAIM_MANAGE = "phc.reimbursement.manage"
P_CLAIM_APPROVE = "phc.reimbursement.approve"
P_INVENTORY_VIEW = "phc.inventory.view"
P_INVENTORY_CREATE = "phc.inventory.create"
P_INVENTORY_UPDATE = "phc.inventory.update"
P_REQUISITION_VIEW = "phc.requisition.view"
P_REQUISITION_CREATE = "phc.requisition.create"
P_REQUISITION_APPROVE = "phc.requisition.approve"
P_REQUISITION_UPDATE = "phc.requisition.update"
P_AMBULANCE_VIEW = "phc.ambulance_usage.view"
P_AMBULANCE_CREATE = "phc.ambulance_usage.create"
P_ADVISORY_VIEW = "phc.advisory.view"
P_ADVISORY_PUBLISH = "phc.advisory.publish"
P_REPORT_VIEW = "phc.report.view"
P_NOTIFICATION_VIEW = "phc.notification.view"


def _actor(request):
    return request.principal


def _page(view, request, queryset, serializer):
    paginator = CursorPagination()
    paginator.page_size = 25
    page = paginator.paginate_queryset(queryset, request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


class DoctorAvailabilityView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_SCHEDULE_VIEW)]

    @extend_schema(responses=s.ScheduleAvailabilitySerializer(many=True), examples=[
        OpenApiExample("Published weekly availability", value=[{
            "id": 4, "doctor": {"id": 2, "display_name": "Doctor",
                                  "specialization": "General Medicine",
                                  "is_active": True},
            "day_of_week": 1, "starts_at": "09:00:00", "ends_at": "12:00:00",
            "publication": "published", "attendance_status": "available",
        }], response_only=True)])
    def get(self, request):
        rows = list(scoping.schedules_for_patients())
        attendance = dict(DoctorAttendance.objects.filter(
            attendance_date=timezone.localdate(),
            doctor_id__in={row.doctor_id for row in rows},
        ).values_list("doctor_id", "status"))
        data = s.ScheduleAvailabilitySerializer(rows, many=True).data
        for row, slot in zip(data, rows, strict=True):
            row["attendance_status"] = attendance.get(slot.doctor_id)
        return Response(data)


class PatientRecordsView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_RECORD_VIEW)]

    @extend_schema(responses=s.PatientVisitSerializer(many=True), examples=[
        OpenApiExample("Own medical history", value=[{
            "id": 12, "patient_user_id": 1001, "visited_on": "2026-11-01",
            "notes": "Clinical notes", "recorded_by_user_id": 8,
            "prescriptions": [], "created_at": "2026-11-01T08:00:00Z",
        }], response_only=True)])
    def get(self, request):
        return _page(self, request, scoping.visits_for(_actor(request)),
                     s.PatientVisitSerializer)


class PatientRecordsPdfView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_RECORD_EXPORT)]
    throttle_scope = "phc_pdf"

    @extend_schema(request=s.MedicalPdfRequestSerializer,
                   responses={200: OpenApiResponse(
                       response=OpenApiTypes.BINARY,
                       description="PDF containing the caller's selected medical history.")},
                   examples=[OpenApiExample("Export selected visits", value={
                       "visit_ids": [12, 18],
                   }, request_only=True)])
    def post(self, request):
        payload = s.MedicalPdfRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        content = pdf_service.patient_records_pdf(
            actor=_actor(request), visit_ids=payload.validated_data["visit_ids"])
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="medical-records.pdf"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PatientSearchView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_RECORD_CREATE)]

    @extend_schema(responses=s.PatientSearchSerializer(many=True), examples=[
        OpenApiExample("Directory matches", value=[{
            "user_id": 1001, "display_name": "Institute Member", "kind": "staff",
        }], response_only=True)])
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) > 80:
            raise BadRequestError("Keep the patient search under 80 characters.",
                                  code="search_too_long")
        rows = directory.search(q=query, limit=25)
        data = [{"user_id": row.user_id, "display_name": row.display_name,
                 "kind": row.kind} for row in rows]
        return Response(s.PatientSearchSerializer(data, many=True).data)


class PatientVisitCreateView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_RECORD_CREATE)]
    throttle_scope = "phc_write"

    @extend_schema(request=s.VisitWriteSerializer, responses=s.PatientVisitSerializer,
                   examples=[OpenApiExample("Record visit", value={
                       "patient_user_id": 1001, "visited_on": "2026-11-23",
                       "notes": "Symptoms and clinical remarks",
                       "prescription_details": "Medicine and dosage instructions",
                       "issued_on": "2026-11-23",
                   }, request_only=True)])
    def post(self, request):
        payload = s.VisitWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = records_service.create_visit(
            **payload.validated_data, actor_user_id=_actor(request).user_id)
        return Response(s.PatientVisitSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ScheduleListCreateView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE_GATE(), HasPermission(P_SCHEDULE_CREATE)()]
        return [MODULE_GATE(), HasPermission(P_SCHEDULE_VIEW)()]

    @extend_schema(responses=s.ScheduleSlotSerializer(many=True), examples=[
        OpenApiExample("Schedule slots", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, scoping.staff_schedules(), s.ScheduleSlotSerializer)

    @extend_schema(request=s.ScheduleSlotPatchSerializer,
                   responses=s.ScheduleSlotSerializer,
                   examples=[OpenApiExample("Create weekly slot", value={
                       "display_name": "Visiting Doctor", "specialization": "General Medicine",
                       "day_of_week": 1, "starts_at": "09:00:00", "ends_at": "12:00:00",
                   }, request_only=True)])
    def post(self, request):
        payload = s.ScheduleSlotWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = schedule_service.create_doctor_slot(
            doctor_id=data.get("doctor_id"),
            display_name=data.get("display_name", ""),
            specialization=data.get("specialization", ""),
            day_of_week=data["day_of_week"], starts_at=data["starts_at"],
            ends_at=data["ends_at"], actor_user_id=_actor(request).user_id)
        return Response(s.ScheduleSlotSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ScheduleSlotView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_SCHEDULE_UPDATE)]
    throttle_scope = "phc_write"

    @extend_schema(request=s.ScheduleSlotWriteSerializer,
                   responses=s.ScheduleSlotSerializer,
                   examples=[OpenApiExample("Update slot", value={
                       "day_of_week": 2, "starts_at": "10:00:00", "ends_at": "13:00:00",
                   }, request_only=True)])
    def patch(self, request, pk):
        instance = DoctorScheduleSlot.objects.filter(pk=pk).first()
        payload = s.ScheduleSlotPatchSerializer(instance=instance, data=request.data,
                                                partial=True)
        payload.is_valid(raise_exception=True)
        allowed = {"day_of_week", "starts_at", "ends_at"}
        changes = {key: value for key, value in payload.validated_data.items()
                   if key in allowed}
        if not changes:
            raise BadRequestError("Change a day or schedule time.", code="empty_update")
        row = schedule_service.update_slot(
            slot_id=pk, changes=changes, actor_user_id=_actor(request).user_id)
        return Response(s.ScheduleSlotSerializer(row).data)


class SchedulePublishView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_SCHEDULE_PUBLISH)]
    throttle_scope = "phc_write"

    @extend_schema(request=None, responses=s.ScheduleSlotSerializer,
                   examples=[OpenApiExample("Published slot", value={
                       "id": 4, "publication": "published",
                   }, response_only=True)])
    def post(self, request, pk):
        row = schedule_service.publish_slot(
            slot_id=pk, actor_user_id=_actor(request).user_id)
        return Response(s.ScheduleSlotSerializer(row).data)


class AttendanceView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_ATTENDANCE_UPDATE)]
    throttle_scope = "phc_write"

    @extend_schema(responses=s.AttendanceSerializer(many=True), examples=[
        OpenApiExample("Today's attendance", value=[], response_only=True)])
    def get(self, request):
        rows = DoctorAttendance.objects.filter(
            attendance_date=timezone.localdate(), doctor__is_active=True
        ).select_related("doctor").order_by("doctor__display_name", "id")
        return _page(self, request, rows, s.AttendanceSerializer)

    @extend_schema(request=s.AttendanceWriteSerializer,
                   responses=s.AttendanceSerializer,
                   examples=[OpenApiExample("Mark available", value={
                       "doctor_id": 2, "status": "available",
                   }, request_only=True)])
    def post(self, request):
        payload = s.AttendanceWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = schedule_service.set_attendance(
            **payload.validated_data, attendance_date=timezone.localdate(),
            actor_user_id=_actor(request).user_id)
        return Response(s.AttendanceSerializer(row).data)


class ClaimsView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE_GATE(), HasPermission(P_CLAIM_CREATE)()]
        return [MODULE_GATE(), HasPermission(P_CLAIM_VIEW)()]

    @extend_schema(responses=s.ReimbursementSerializer(many=True), examples=[
        OpenApiExample("Claim history", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, scoping.claims_for(_actor(request)),
                     s.ReimbursementSerializer)

    @extend_schema(request=s.ReimbursementWriteSerializer,
                   responses=s.ReimbursementSerializer,
                   examples=[OpenApiExample("Submit reimbursement claim", value={
                       "prescription_id": 13, "claim_amount": "1250.00",
                       "expense_date": "2026-11-01", "bill_reference": "BILL-23",
                       "remarks": "Consultation expense",
                   }, request_only=True)])
    def post(self, request):
        payload = s.ReimbursementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        bill_reference = data.pop("bill_reference", "")
        remarks = data.pop("remarks", "")
        row = reimbursement_service.submit_claim(
            claimant_user_id=_actor(request).user_id,
            bill_reference=bill_reference, remarks=remarks, **data)
        return Response(s.ReimbursementSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ClaimTransitionView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        event = self.kwargs.get("event", getattr(self, "event", "review"))
        permission = {
            "review": P_CLAIM_REVIEW,
            "verification": P_CLAIM_MANAGE,
            "sanction": P_CLAIM_APPROVE,
            "payment": P_CLAIM_MANAGE,
        }[event]
        return [MODULE_GATE(), HasPermission(permission)()]

    @extend_schema(request=None, responses=s.ReimbursementSerializer,
                   examples=[OpenApiExample("Claim stage changed", value={
                       "id": 21, "state": "pending_accounts_verification",
                   }, response_only=True)])
    def post(self, request, pk, event):
        row = reimbursement_service.transition_claim(
            claim_id=pk, actor_user_id=_actor(request).user_id,
            actor_role=scoping.active_role(_actor(request)),
            event={"verification": "verify", "payment": "pay"}.get(event, event),
            scope=scoping.claims_for(_actor(request)))
        return Response(s.ReimbursementSerializer(row).data)


class ClaimSanctionView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_CLAIM_APPROVE)]
    throttle_scope = "phc_write"

    @extend_schema(request=s.SanctionDecisionSerializer,
                   responses=s.ReimbursementSerializer,
                   examples=[OpenApiExample("Approve sanction", value={
                       "decision": "approve",
                   }, request_only=True)])
    def post(self, request, pk):
        payload = s.SanctionDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = reimbursement_service.transition_claim(
            claim_id=pk, actor_user_id=_actor(request).user_id,
            actor_role=scoping.active_role(_actor(request)),
            event=payload.validated_data["decision"],
            scope=scoping.claims_for(_actor(request)))
        return Response(s.ReimbursementSerializer(row).data)


class InventoryView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        permission = P_INVENTORY_CREATE if self.request.method == "POST" else P_INVENTORY_VIEW
        return [MODULE_GATE(), HasPermission(permission)()]

    @extend_schema(responses=s.InventoryItemSerializer(many=True), examples=[
        OpenApiExample("Inventory items", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, inventory_selectors.items_with_stock(),
                     s.InventoryItemSerializer)

    @extend_schema(request=s.InventoryItemWriteSerializer,
                   responses=s.InventoryItemSerializer,
                   examples=[OpenApiExample("Create item", value={
                       "name": "Bandage", "unit": "units", "reorder_threshold": 10,
                   }, request_only=True)])
    def post(self, request):
        payload = s.InventoryItemWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = inventory_service.create_item(**payload.validated_data)
        item.stock_quantity = 0
        return Response(s.InventoryItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


class InventoryMovementView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_INVENTORY_UPDATE)]
    throttle_scope = "phc_write"

    @extend_schema(request=s.StockAdjustmentSerializer,
                   responses=s.InventoryMovementSerializer,
                   examples=[OpenApiExample("Add stock", value={
                       "quantity_delta": 25, "reason": "Supply received",
                   }, request_only=True)])
    def post(self, request, pk):
        payload = s.StockAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        _, quantity, movement = inventory_service.adjust_stock(
            item_id=pk, actor_user_id=_actor(request).user_id,
            **payload.validated_data)
        movement.quantity_after = quantity
        return Response({**s.InventoryMovementSerializer(movement).data,
                         "quantity_after": quantity}, status=status.HTTP_201_CREATED)


class LowStockAlertsView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_INVENTORY_VIEW)]

    @extend_schema(responses=s.LowStockAlertSerializer(many=True), examples=[
        OpenApiExample("Low-stock alerts", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, inventory_selectors.low_stock_alerts(),
                     s.LowStockAlertSerializer)


class RequisitionsView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE_GATE(), HasPermission(P_REQUISITION_CREATE)()]
        return [MODULE_GATE(), HasPermission(P_REQUISITION_VIEW)()]

    @extend_schema(responses=s.RequisitionSerializer(many=True), examples=[
        OpenApiExample("Requisition list", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, scoping.requisitions_for(_actor(request)),
                     s.RequisitionSerializer)

    @extend_schema(request=s.RequisitionWriteSerializer,
                   responses=s.RequisitionSerializer,
                   examples=[OpenApiExample("Submit requisition", value={
                       "lines": [{"item_id": 4, "quantity": 12}],
                   }, request_only=True)])
    def post(self, request):
        payload = s.RequisitionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = requisition_service.submit_requisition(
            actor_user_id=_actor(request).user_id,
            lines=payload.validated_data["lines"])
        row = scoping.requisitions_for(_actor(request)).get(pk=row.pk)
        return Response(s.RequisitionSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class RequisitionDecisionView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_REQUISITION_APPROVE)]
    throttle_scope = "phc_write"

    @extend_schema(request=s.SanctionDecisionSerializer,
                   responses=s.RequisitionSerializer,
                   examples=[OpenApiExample("Approve requisition", value={
                       "decision": "approve",
                   }, request_only=True)])
    def post(self, request, pk):
        payload = s.SanctionDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = requisition_service.transition_requisition(
            requisition_id=pk, actor_user_id=_actor(request).user_id,
            actor_role=scoping.active_role(_actor(request)),
            event=payload.validated_data["decision"],
            scope=scoping.requisitions_for(_actor(request)))
        return Response(s.RequisitionSerializer(row).data)


class RequisitionFulfillView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_REQUISITION_UPDATE)]
    throttle_scope = "phc_write"

    @extend_schema(request=None, responses=s.RequisitionSerializer,
                   examples=[OpenApiExample("Fulfilled", value={
                       "id": 32, "state": "fulfilled",
                   }, response_only=True)])
    def post(self, request, pk):
        row = requisition_service.transition_requisition(
            requisition_id=pk, actor_user_id=_actor(request).user_id,
            actor_role=scoping.active_role(_actor(request)), event="fulfill",
            scope=scoping.requisitions_for(_actor(request)))
        return Response(s.RequisitionSerializer(row).data)


class AmbulanceUsageView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        permission = P_AMBULANCE_CREATE if self.request.method == "POST" else P_AMBULANCE_VIEW
        return [MODULE_GATE(), HasPermission(permission)()]

    @extend_schema(responses=s.AmbulanceUsageSerializer(many=True), examples=[
        OpenApiExample("Ambulance log", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, scoping.ambulance_logs(), s.AmbulanceUsageSerializer)

    @extend_schema(request=s.AmbulanceUsageWriteSerializer,
                   responses=s.AmbulanceUsageSerializer,
                   examples=[OpenApiExample("Record use", value={
                       "used_at": "2026-11-23T10:30:00+05:30",
                       "patient_name": "Patient Name", "destination": "Hospital",
                   }, request_only=True)])
    def post(self, request):
        payload = s.AmbulanceUsageWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = operations_service.record_ambulance_usage(
            **payload.validated_data, actor_user_id=_actor(request).user_id)
        return Response(s.AmbulanceUsageSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class AdvisoriesView(APIView):
    throttle_scope = "phc_write"

    def get_permissions(self):
        permission = P_ADVISORY_PUBLISH if self.request.method == "POST" else P_ADVISORY_VIEW
        return [MODULE_GATE(), HasPermission(permission)()]

    @extend_schema(responses=s.HealthAdvisorySerializer(many=True), examples=[
        OpenApiExample("Published advisories", value=[], response_only=True)])
    def get(self, request):
        queryset = (scoping.advisories_for_staff() if scoping.is_compounder(_actor(request))
                    else scoping.advisories_for_patients())
        return _page(self, request, queryset, s.HealthAdvisorySerializer)

    @extend_schema(request=s.HealthAdvisoryWriteSerializer,
                   responses=s.HealthAdvisorySerializer,
                   examples=[OpenApiExample("Publish advisory", value={
                       "title": "Seasonal health advisory", "body": "Advisory details",
                   }, request_only=True)])
    def post(self, request):
        payload = s.HealthAdvisoryWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = operations_service.publish_advisory(
            **payload.validated_data, actor_user_id=_actor(request).user_id)
        return Response(s.HealthAdvisorySerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ReportsView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_REPORT_VIEW)]

    @extend_schema(responses=s.ReportSerializer, examples=[
        OpenApiExample("Aggregate report", value={
            "report_type": "visits", "data": {"total": 0, "by_month": []},
        }, response_only=True)])
    def get(self, request, report_type):
        try:
            data = report_service.aggregate_report(report_type)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="report_type_invalid") from exc
        return Response({"report_type": report_type, "data": data})


class NotificationsView(APIView):
    permission_classes = [MODULE_GATE, HasPermission(P_NOTIFICATION_VIEW)]

    @extend_schema(responses=s.NotificationSerializer(many=True), examples=[
        OpenApiExample("Notifications", value=[], response_only=True)])
    def get(self, request):
        return _page(self, request, scoping.notifications_for(_actor(request)),
                     s.NotificationSerializer)
