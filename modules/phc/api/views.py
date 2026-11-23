"""HTTP layer: parse, scope, delegate, serialise. Module grant first, then the permission."""
from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, DomainError, NotFoundError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.phc.api import serializers as s
from modules.phc.domain import reports as report_rules
from modules.phc.selectors import patients as patient_selectors
from modules.phc.selectors import reports as report_selectors
from modules.phc.selectors import scoping
from modules.phc.services import inventory as inventory_service
from modules.phc.services import operations as operations_service
from modules.phc.services import records as records_service
from modules.phc.services import reimbursements as claim_service
from modules.phc.services import requisitions as requisition_service
from modules.phc.services import schedules as schedule_service

MODULE = HasModuleGrant("phc")
WRITE_SCOPE = "phc_write"
MAX_PDF_RECORDS = 50


class DirectoryUnavailableError(DomainError):
    code = "directory_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "The institute directory cannot be reached right now. Try the search again shortly."


def _actor(request):
    return getattr(request, "principal", None)


def _example(name, value, *, request=False):
    return OpenApiExample(name, value=value, request_only=request, response_only=not request)


class _Gates:
    # PHC-BR-03: HTTP method -> the permission codes, any one of which admits the caller.
    method_permissions: dict[str, tuple[str, ...]] = {}

    def get_permissions(self):
        codes = self.method_permissions.get(self.request.method)
        if not codes:
            codes = self.method_permissions.get("GET", ("phc.__none__",))
        return [MODULE(), HasPermission(*codes)()]

    def get_throttles(self):
        self.throttle_scope = WRITE_SCOPE if self.request.method != "GET" else None
        return super().get_throttles()


class _PhcView(_Gates, generics.GenericAPIView):
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["actor"] = _actor(self.request)
        return ctx


SCHEDULE_OUT = {"id": 3, "doctor_name": "Dr. R. Iyer", "specialization": "General Medicine",
                "is_published": True, "published_at": "2026-11-20T09:00:00+05:30",
                "slots": [{"day_of_week": 0, "day_label": "Monday", "start_time": "10:00:00",
                           "end_time": "13:00:00"}], "today_status": "available"}
SCHEDULE_IN = {"doctor_name": "Dr. R. Iyer", "specialization": "General Medicine",
               "slots": [{"day_of_week": 0, "start_time": "10:00", "end_time": "13:00"}]}


# -- Schedules (PHC-UC-01, PHC-UC-07, PHC-UC-08, PHC-UC-22) ---------------------------
@extend_schema(request=s.ScheduleWriteSerializer, responses=s.ScheduleSerializer,
               examples=[_example("Create", SCHEDULE_IN, request=True),
                         _example("Schedule", SCHEDULE_OUT)])
class ScheduleListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.ScheduleSerializer
    pagination_class = None
    method_permissions = {"GET": ("phc.schedule.view",), "POST": ("phc.schedule.create",)}

    def get_queryset(self):
        return scoping.schedules_for(_actor(self.request), today=timezone.localdate())

    def create(self, request, *args, **kwargs):
        payload = s.ScheduleWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        schedule = schedule_service.create_schedule(actor=_actor(request),
                                                    **payload.validated_data)
        return Response(s.ScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.ScheduleWriteSerializer, responses=s.ScheduleSerializer,
               examples=[_example("Update", SCHEDULE_IN, request=True),
                         _example("Schedule", SCHEDULE_OUT)])
class ScheduleDetailView(_Gates, APIView):
    method_permissions = {"PUT": ("phc.schedule.update",)}

    def put(self, request, pk):
        payload = s.ScheduleWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        schedule = schedule_service.update_schedule(actor=_actor(request), schedule_id=pk,
                                                    **payload.validated_data)
        return Response(s.ScheduleSerializer(schedule).data)


@extend_schema(request=None, responses=s.ScheduleSerializer,
               examples=[_example("Published", SCHEDULE_OUT)])
class SchedulePublishView(_Gates, APIView):
    method_permissions = {"POST": ("phc.schedule.publish",)}

    def post(self, request, pk):
        schedule = schedule_service.publish_schedule(actor=_actor(request), schedule_id=pk)
        return Response(s.ScheduleSerializer(schedule).data)


@extend_schema(request=s.AttendanceWriteSerializer, responses=s.AttendanceSerializer,
               examples=[_example("Arrived", {"status": "available"}, request=True),
                         _example("Attendance", {"schedule": 3, "attendance_date": "2026-11-23",
                                                 "status": "available"})])
class AttendanceView(_Gates, APIView):
    method_permissions = {"POST": ("phc.attendance.update",)}

    def post(self, request, pk):
        payload = s.AttendanceWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = schedule_service.mark_attendance(actor=_actor(request), schedule_id=pk,
                                               status=payload.validated_data["status"])
        return Response(s.AttendanceSerializer(row).data)


# -- Patients and records (PHC-UC-02, PHC-UC-03, PHC-UC-06) ---------------------------
@extend_schema(parameters=[OpenApiParameter("q", str, required=True)],
               responses=s.PatientSerializer(many=True),
               examples=[_example("Match", [{"user_id": 4021, "display_name": "A. Sharma",
                                             "kind": "staff"}])])
class PatientSearchView(_Gates, APIView):
    method_permissions = {"GET": ("phc.patient.view",)}

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        # AFR-PHC-006
        if len(q) < patient_selectors.MIN_QUERY:
            raise BadRequestError("Type at least two characters to search for a patient.",
                                  code="search_too_short")
        try:
            people = patient_selectors.search_patients(q)
        except IamUnavailable as exc:
            raise DirectoryUnavailableError() from exc
        return Response(s.PatientSerializer(people, many=True).data)


VISIT_OUT = {"id": 11, "patient_user_id": 4021, "visit_date": "2026-11-21",
             "complaint": "Fever", "diagnosis": "Viral fever",
             "prescriptions": [{"id": 17, "medicine": "Paracetamol 500mg", "dosage": "1-0-1",
                                "duration_days": 3, "instructions": "After food"}],
             "created_at": "2026-11-21T10:15:00+05:30"}


@extend_schema(request=s.VisitWriteSerializer, responses=s.VisitSerializer,
               examples=[_example("Record", {"patient_user_id": 4021,
                                             "visit_date": "2026-11-21", "complaint": "Fever",
                                             "diagnosis": "Viral fever",
                                             "prescriptions": [{"medicine": "Paracetamol 500mg",
                                                                "dosage": "1-0-1",
                                                                "duration_days": 3,
                                                                "instructions": "After food"}]},
                                  request=True),
                         _example("Visit", VISIT_OUT)])
class VisitListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.VisitSerializer
    method_permissions = {"GET": ("phc.record.view",), "POST": ("phc.record.create",)}

    def get_queryset(self):
        return scoping.visits_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        payload = s.VisitWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = records_service.record_visit(actor=_actor(request), **payload.validated_data)
        return Response(s.VisitSerializer(visit).data, status=status.HTTP_201_CREATED)


@extend_schema(responses=s.VisitSerializer, examples=[_example("Visit", VISIT_OUT)])
class VisitDetailView(_PhcView, generics.RetrieveAPIView):
    serializer_class = s.VisitSerializer
    method_permissions = {"GET": ("phc.record.view",)}

    def get_queryset(self):
        return scoping.visits_for(_actor(self.request))


def _ids_param(raw: str) -> list[int]:
    try:
        ids = sorted({int(part) for part in raw.split(",") if part.strip()})
    except ValueError as exc:
        raise BadRequestError("ids must be a comma-separated list of record numbers.",
                              code="invalid_filter") from exc
    if not ids:
        raise BadRequestError("Choose at least one record to download.", code="no_records")
    if len(ids) > MAX_PDF_RECORDS:
        raise BadRequestError(f"Download at most {MAX_PDF_RECORDS} records at a time.",
                              code="too_many_records")
    return ids


@extend_schema(parameters=[OpenApiParameter("ids", str, required=True,
                                            description="Comma-separated visit ids")],
               responses={(200, "application/pdf"): OpenApiTypes.BINARY},
               examples=[_example("PDF", "%PDF-1.4 ...")])
class RecordsPdfView(_Gates, APIView):
    method_permissions = {"GET": ("phc.record.view",)}

    def get(self, request):
        ids = _ids_param(request.query_params.get("ids", ""))
        visits = list(scoping.visits_for(_actor(request)).filter(pk__in=ids))
        if len(visits) != len(ids):
            raise NotFoundError("One of those records does not exist.")
        body = records_service.records_pdf(visits)
        response = HttpResponse(body, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="phc-medical-records.pdf"'
        return response


# -- Claims (PHC-UC-04, PHC-UC-05, PHC-UC-15, PHC-UC-19, PHC-UC-20, PHC-UC-21) -------
CLAIM_OUT = {"id": 7, "user_id": 4021, "prescription": 17,
             "prescription_label": "Paracetamol 500mg (2026-11-21)",
             "expense_date": "2026-11-21", "amount": "450.00", "description": "Pharmacy bill",
             "status": "pending_phc_review", "status_label": "Pending PHC review",
             "submitted_at": "2026-11-22T11:00:00+05:30",
             "actions": [{"event": "submit", "from_status": "",
                          "to_status": "pending_phc_review", "note": "",
                          "created_at": "2026-11-22T11:00:00+05:30"}],
             "allowed_events": []}


@extend_schema(request=s.ClaimWriteSerializer, responses=s.ClaimSerializer,
               examples=[_example("Submit", {"prescription_id": 17, "expense_date": "2026-11-21",
                                             "amount": "450.00",
                                             "description": "Pharmacy bill"}, request=True),
                         _example("Claim", CLAIM_OUT)])
class ClaimListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.ClaimSerializer
    method_permissions = {"GET": ("phc.claim.view",), "POST": ("phc.claim.create",)}

    def get_queryset(self):
        qs = scoping.claims_for(_actor(self.request))
        wanted = self.request.query_params.get("status")
        if wanted:
            if wanted not in claim_service.STATUS_LABELS:
                raise BadRequestError("Unknown claim status.", code="invalid_filter")
            qs = qs.filter(status=wanted)
        return qs

    def create(self, request, *args, **kwargs):
        payload = s.ClaimWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        claim = claim_service.submit_claim(actor=_actor(request), **payload.validated_data)
        claim = scoping.claims_for(_actor(request)).get(pk=claim.pk)
        return Response(s.ClaimSerializer(claim, context={"actor": _actor(request)}).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(responses=s.ClaimSerializer, examples=[_example("Claim", CLAIM_OUT)])
class ClaimDetailView(_PhcView, generics.RetrieveAPIView):
    serializer_class = s.ClaimSerializer
    method_permissions = {"GET": ("phc.claim.view",)}

    def get_queryset(self):
        return scoping.claims_for(_actor(self.request))


@extend_schema(request=s.ClaimTransitionSerializer, responses=s.ClaimSerializer,
               examples=[_example("Forward", {"event": "forward", "note": ""}, request=True),
                         _example("Claim", {**CLAIM_OUT,
                                            "status": "pending_accounts_verification"})])
class ClaimTransitionView(_Gates, APIView):
    method_permissions = {"POST": ("phc.claim.review", "phc.claim.update", "phc.claim.approve",
                                   "phc.claim.create")}

    def post(self, request, pk):
        payload = s.ClaimTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        claim_service.transition_claim(actor=_actor(request), claim_id=pk,
                                       **payload.validated_data)
        claim = scoping.claims_for(_actor(request)).get(pk=pk)
        return Response(s.ClaimSerializer(claim, context={"actor": _actor(request)}).data)


@extend_schema(responses=s.EligiblePrescriptionSerializer(many=True),
               examples=[_example("Prescriptions", [{"id": 17, "medicine": "Paracetamol 500mg",
                                                     "dosage": "1-0-1",
                                                     "visit_date": "2026-11-21"}])])
class ClaimPrescriptionsView(_PhcView, generics.ListAPIView):
    serializer_class = s.EligiblePrescriptionSerializer
    pagination_class = None
    method_permissions = {"GET": ("phc.claim.create",)}

    def get_queryset(self):
        return (scoping.own_prescriptions(_actor(self.request)).select_related("visit")
                .order_by("-visit__visit_date", "-id"))


# -- Inventory (PHC-UC-09) -----------------------------------------------------------
ITEM_OUT = {"id": 5, "name": "Paracetamol 500mg", "unit": "strip", "stock_level": "40.00",
            "reorder_threshold": "50.00", "is_low": True}


@extend_schema(request=s.InventoryItemWriteSerializer, responses=s.InventoryItemSerializer,
               examples=[_example("Add item", {"name": "Paracetamol 500mg", "unit": "strip",
                                               "stock_level": "100", "reorder_threshold": "50"},
                                  request=True),
                         _example("Item", ITEM_OUT)])
class InventoryListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.InventoryItemSerializer
    method_permissions = {"GET": ("phc.inventory.view",), "POST": ("phc.inventory.create",)}

    def get_queryset(self):
        return scoping.inventory_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        payload = s.InventoryItemWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = inventory_service.create_item(actor=_actor(request), **payload.validated_data)
        return Response(s.InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.StockAdjustmentWriteSerializer, responses=s.StockAdjustmentSerializer,
               examples=[_example("Deduct", {"delta": "-60", "reason": "Dispensed"},
                                  request=True),
                         _example("Adjustment", {"id": 9, "item": 5, "delta": "-60.00",
                                                 "level_after": "40.00", "reason": "Dispensed",
                                                 "created_at": "2026-11-23T12:00:00+05:30",
                                                 "low_stock_alert": True})])
class StockAdjustView(_Gates, APIView):
    method_permissions = {"POST": ("phc.inventory.update",)}

    def post(self, request, pk):
        payload = s.StockAdjustmentWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        adjustment = inventory_service.adjust_stock(actor=_actor(request), item_id=pk,
                                                    **payload.validated_data)
        return Response(s.StockAdjustmentSerializer(adjustment).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(responses=s.LowStockAlertSerializer,
               examples=[_example("Alert", {"id": 2, "item": 5, "item_name": "Paracetamol 500mg",
                                            "level": "40.00", "threshold": "50.00",
                                            "created_at": "2026-11-23T12:00:00+05:30"})])
class LowStockAlertListView(_PhcView, generics.ListAPIView):
    serializer_class = s.LowStockAlertSerializer
    method_permissions = {"GET": ("phc.inventory.view",)}

    def get_queryset(self):
        return scoping.alerts_for(_actor(self.request))


# -- Requisitions (PHC-UC-10, PHC-UC-14, PHC-UC-16) ----------------------------------
REQUISITION_OUT = {"id": 4, "originator_user_id": 3001, "purpose": "Monthly restock",
                   "status": "pending_approval", "status_label": "Pending approval",
                   "lines": [{"item": 5, "item_name": "Paracetamol 500mg", "unit": "strip",
                              "quantity": "200.00"}],
                   "decision_note": "", "decided_at": None, "fulfilled_at": None,
                   "created_at": "2026-11-23T12:30:00+05:30", "allowed_events": []}


@extend_schema(request=s.RequisitionWriteSerializer, responses=s.RequisitionSerializer,
               examples=[_example("Raise", {"purpose": "Monthly restock",
                                            "lines": [{"item_id": 5, "quantity": "200"}]},
                                  request=True),
                         _example("Requisition", REQUISITION_OUT)])
class RequisitionListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.RequisitionSerializer
    method_permissions = {"GET": ("phc.requisition.view",),
                          "POST": ("phc.requisition.create",)}

    def get_queryset(self):
        return scoping.requisitions_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        payload = s.RequisitionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = requisition_service.submit(actor=_actor(request), **payload.validated_data)
        req = scoping.requisitions_for(_actor(request)).get(pk=req.pk)
        return Response(s.RequisitionSerializer(req, context={"actor": _actor(request)}).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.RequisitionTransitionSerializer, responses=s.RequisitionSerializer,
               examples=[_example("Approve", {"event": "approve", "note": ""}, request=True),
                         _example("Requisition", {**REQUISITION_OUT, "status": "approved"})])
class RequisitionTransitionView(_Gates, APIView):
    method_permissions = {"POST": ("phc.requisition.approve", "phc.requisition.update")}

    def post(self, request, pk):
        payload = s.RequisitionTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        requisition_service.transition(actor=_actor(request), requisition_id=pk,
                                       **payload.validated_data)
        req = scoping.requisitions_for(_actor(request)).get(pk=pk)
        return Response(s.RequisitionSerializer(req, context={"actor": _actor(request)}).data)


# -- Ambulance (PHC-UC-11), advisories (PHC-UC-12) -----------------------------------
AMBULANCE_IN = {"used_at": "2026-11-23T08:40:00+05:30", "patient_name": "Hostel 4 resident",
                "destination": "District Hospital"}


@extend_schema(request=s.AmbulanceLogSerializer, responses=s.AmbulanceLogSerializer,
               examples=[_example("Log", AMBULANCE_IN, request=True),
                         _example("Entry", {"id": 1, **AMBULANCE_IN,
                                            "created_at": "2026-11-23T09:00:00+05:30"})])
class AmbulanceListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.AmbulanceLogSerializer
    method_permissions = {"GET": ("phc.ambulance.view",), "POST": ("phc.ambulance.create",)}

    def get_queryset(self):
        return scoping.ambulance_logs_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        payload = s.AmbulanceLogSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = operations_service.log_ambulance(actor=_actor(request), **payload.validated_data)
        return Response(s.AmbulanceLogSerializer(row).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.AdvisorySerializer, responses=s.AdvisorySerializer,
               examples=[_example("Publish", {"title": "Dengue precautions",
                                              "body": "Remove standing water."}, request=True),
                         _example("Advisory", {"id": 2, "title": "Dengue precautions",
                                               "body": "Remove standing water.",
                                               "published_at": "2026-11-23T09:00:00+05:30"})])
class AdvisoryListView(_PhcView, generics.ListCreateAPIView):
    serializer_class = s.AdvisorySerializer
    method_permissions = {"GET": ("phc.advisory.view",), "POST": ("phc.advisory.publish",)}

    def get_queryset(self):
        return scoping.advisories_for(_actor(self.request))

    def create(self, request, *args, **kwargs):
        payload = s.AdvisorySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = operations_service.publish_advisory(actor=_actor(request),
                                                  **payload.validated_data)
        return Response(s.AdvisorySerializer(row).data, status=status.HTTP_201_CREATED)


# -- Reports (PHC-UC-13), notifications ----------------------------------------------
@extend_schema(parameters=[s.ReportQuerySerializer],
               responses=s.ReportSerializer,
               examples=[_example("Utilization", {"category": "utilization",
                                                  "start": "2026-11-01", "end": "2026-11-30",
                                                  "data": {"visits_by_month": [
                                                      {"month": "2026-11", "visits": 42}],
                                                      "claims_by_status": {"reimbursed": 6}}})])
class ReportView(_Gates, APIView):
    method_permissions = {"GET": ("phc.report.view",)}

    def get(self, request):
        params = s.ReportQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        try:
            req = report_rules.validate_request(**params.validated_data)
        except report_rules.ReportParameterError as exc:
            raise BadRequestError(str(exc), code="invalid_report") from exc
        return Response(report_selectors.build(req))


@extend_schema(responses=s.NotificationSerializer,
               examples=[_example("Notification", {"id": 8, "kind": "claim_status",
                                                   "message": "Your reimbursement claim #7 is "
                                                              "now reimbursed.",
                                                   "resource_type": "reimbursement_claim",
                                                   "resource_id": 7,
                                                   "created_at": "2026-11-23T15:00:00+05:30"})])
class NotificationListView(_PhcView, generics.ListAPIView):
    serializer_class = s.NotificationSerializer
    method_permissions = {"GET": ("phc.notification.view",)}

    def get_queryset(self):
        return scoping.notifications_for(_actor(self.request))
