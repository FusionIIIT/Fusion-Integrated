"""HTTP layer: parse, scope, delegate, serialise. No state logic lives here;
the services own it. The caller is always `request.principal`."""
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.oap.api import serializers as s
from modules.oap.domain import assistantship as assistantship_rules
from modules.oap.domain import bonafide as bonafide_rules
from modules.oap.domain import leave as leave_rules
from modules.oap.domain import nodues as nodues_rules
from modules.oap.domain import seminar as seminar_rules
from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    LeaveApplication,
    NoDuesRequest,
    SeminarRequest,
    SupervisorAssignment,
    TAAssignment,
)
from modules.oap.services import assistantship as assistantship_service
from modules.oap.services import bonafide as bonafide_service
from modules.oap.services import leave as leave_service
from modules.oap.services import nodues as nodues_service
from modules.oap.services import records as records_service
from modules.oap.services import seminar as seminar_service
from modules.oap.services.common import ServiceError, department_of

MODULE_CODE = "oap"


def _uid(request):
    return request.principal.user_id


def _fake(view):
    """drf-spectacular builds views without a principal while generating schema."""
    return getattr(view, "swagger_fake_view", False)


def _guarded(call, ok):
    """Run a service call; a refused rule is 400, a missing/foreign row is 404."""
    try:
        result = call()
    except ServiceError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return ok(result)


class _Gated:
    """Module grant plus one permission code per HTTP method."""

    permission_codes = {}

    def get_permissions(self):
        code = self.permission_codes.get(self.request.method)
        if code is None:  # HEAD / OPTIONS follow the first declared method
            code = next(iter(self.permission_codes.values()))
        return [HasModuleGrant(MODULE_CODE)(), HasPermission(code)()]


# -- Leave ---------------------------------------------------------------------
class LeaveListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.LeaveSerializer
    permission_codes = {"GET": "oap.leave.view_self", "POST": "oap.leave.submit"}

    def get_queryset(self):
        if _fake(self):
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(student_id=_uid(self.request))

    @extend_schema(request=s.LeaveSubmitSerializer,
                   responses={201: s.LeaveSerializer})
    def post(self, request, *args, **kwargs):
        payload = s.LeaveSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: leave_service.submit_leave(_uid(request),
                                               **payload.validated_data),
            lambda obj: Response(s.LeaveSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )


class LeavePendingView(_Gated, generics.ListAPIView):
    serializer_class = s.LeaveSerializer
    permission_codes = {"GET": "oap.leave.decide"}

    def get_queryset(self):
        if _fake(self):
            return LeaveApplication.objects.none()
        department = department_of(_uid(self.request))
        if not department:
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(
            status=leave_rules.INITIAL_STATE, department=department
        )


class LeaveDetailView(_Gated, generics.RetrieveAPIView):
    serializer_class = s.LeaveDetailSerializer
    permission_codes = {"GET": "oap.leave.view_self"}

    def get_queryset(self):
        if _fake(self):
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(student_id=_uid(self.request))


class LeaveDecisionView(_Gated, APIView):
    permission_codes = {"POST": "oap.leave.decide"}

    @extend_schema(request=s.DecisionSerializer, responses=s.LeaveSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: leave_service.decide_leave(
                pk, payload.validated_data["action"], _uid(request),
                payload.validated_data["remark"]),
            lambda obj: Response(s.LeaveSerializer(obj).data),
        )


# -- Bonafide ------------------------------------------------------------------
class BonafideListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.BonafideSerializer
    permission_codes = {"GET": "oap.bonafide.view_self",
                        "POST": "oap.bonafide.submit"}

    def get_queryset(self):
        if _fake(self):
            return BonafideRequest.objects.none()
        return BonafideRequest.objects.filter(student_id=_uid(self.request))

    @extend_schema(request=s.BonafideSubmitSerializer,
                   responses={201: s.BonafideSerializer})
    def post(self, request, *args, **kwargs):
        payload = s.BonafideSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: bonafide_service.submit_bonafide(
                _uid(request), payload.validated_data["purpose"]),
            lambda obj: Response(s.BonafideSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )


class BonafidePendingView(_Gated, generics.ListAPIView):
    """The Academic Administrator sees every department (OA-BR-21)."""

    serializer_class = s.BonafideSerializer
    permission_codes = {"GET": "oap.bonafide.decide"}

    def get_queryset(self):
        if _fake(self):
            return BonafideRequest.objects.none()
        return BonafideRequest.objects.filter(status=bonafide_rules.INITIAL_STATE)


class BonafideDetailView(_Gated, generics.RetrieveAPIView):
    serializer_class = s.BonafideDetailSerializer
    permission_codes = {"GET": "oap.bonafide.view_self"}

    def get_queryset(self):
        if _fake(self):
            return BonafideRequest.objects.none()
        return BonafideRequest.objects.filter(student_id=_uid(self.request))


class BonafideDecisionView(_Gated, APIView):
    permission_codes = {"POST": "oap.bonafide.decide"}

    @extend_schema(request=s.DecisionSerializer, responses=s.BonafideSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: bonafide_service.decide_bonafide(
                pk, payload.validated_data["action"], _uid(request),
                payload.validated_data["remark"]),
            lambda obj: Response(s.BonafideSerializer(obj).data),
        )


class BonafideCertificateView(_Gated, APIView):
    permission_codes = {"GET": "oap.bonafide.view_self"}

    @extend_schema(responses=s.BonafideCertificateSerializer)
    def get(self, request, pk):
        def ok(obj):
            data = {
                "certificate_number": obj.certificate_number,
                "student_id": obj.student_id,
                "purpose": obj.purpose,
                "issued_on": obj.decided_at.date() if obj.decided_at else None,
            }
            return Response(s.BonafideCertificateSerializer(data).data)

        return _guarded(
            lambda: bonafide_service.certificate_for(pk, _uid(request)), ok
        )


# -- Seminar -------------------------------------------------------------------
class SeminarListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.SeminarSerializer
    permission_codes = {"GET": "oap.seminar.request", "POST": "oap.seminar.request"}

    def get_queryset(self):
        if _fake(self):
            return SeminarRequest.objects.none()
        return SeminarRequest.objects.filter(student_id=_uid(self.request))

    @extend_schema(request=None, responses={201: s.SeminarSerializer})
    def post(self, request, *args, **kwargs):
        return _guarded(
            lambda: seminar_service.submit_seminar(_uid(request)),
            lambda obj: Response(s.SeminarSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )


class SeminarPendingView(_Gated, generics.ListAPIView):
    serializer_class = s.SeminarSerializer
    permission_codes = {"GET": "oap.seminar.schedule"}

    def get_queryset(self):
        if _fake(self):
            return SeminarRequest.objects.none()
        department = department_of(_uid(self.request))
        if not department:
            return SeminarRequest.objects.none()
        return SeminarRequest.objects.filter(
            status=seminar_rules.INITIAL_STATE, department=department
        )


class SeminarScheduleView(_Gated, APIView):
    permission_codes = {"POST": "oap.seminar.schedule"}

    @extend_schema(request=s.SeminarScheduleSerializer,
                   responses=s.SeminarSerializer)
    def post(self, request, pk):
        payload = s.SeminarScheduleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: seminar_service.schedule_seminar(
                pk, _uid(request), payload.validated_data["scheduled_at"],
                payload.validated_data["venue"]),
            lambda obj: Response(s.SeminarSerializer(obj).data),
        )


class SeminarCalendarView(_Gated, generics.ListAPIView):
    """Visible to PG students and faculty (OA-BR-63)."""

    serializer_class = s.SeminarSerializer
    permission_codes = {"GET": "oap.seminar.view"}

    def get_queryset(self):
        return seminar_service.scheduled_seminars()


# -- No-dues -------------------------------------------------------------------
def _domain_gate(request, domain_code):
    """OA-BR-31: each authority acts only on its own domain. Returns a Response
    to send back, or None when the caller may proceed."""
    if domain_code not in nodues_rules.DOMAIN_CODES:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    if not request.principal.has_permission(
        nodues_rules.verify_permission(domain_code)
    ):
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


class NoDuesListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.NoDuesSerializer
    permission_codes = {"GET": "oap.nodues.view_self", "POST": "oap.nodues.submit"}

    def get_queryset(self):
        if _fake(self):
            return NoDuesRequest.objects.none()
        return NoDuesRequest.objects.filter(student_id=_uid(self.request))

    @extend_schema(request=None, responses={201: s.NoDuesSerializer})
    def post(self, request, *args, **kwargs):
        return _guarded(
            lambda: nodues_service.submit_nodues(_uid(request)),
            lambda obj: Response(s.NoDuesSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )


class NoDuesCompletedView(_Gated, generics.ListAPIView):
    """Verified requests awaiting the Academic Administrator (AFR-OAP-029)."""

    serializer_class = s.NoDuesWithClearancesSerializer
    permission_codes = {"GET": "oap.nodues.finalize"}

    def get_queryset(self):
        if _fake(self):
            return NoDuesRequest.objects.none()
        return NoDuesRequest.objects.filter(
            status__in=(nodues_rules.ALL_CLEAR, nodues_rules.DUES_OUTSTANDING)
        ).prefetch_related("clearances")


class NoDuesPendingView(generics.ListAPIView):
    """Requests still waiting on one authority's domain."""

    serializer_class = s.NoDuesSerializer
    permission_classes = [HasModuleGrant(MODULE_CODE)]

    def list(self, request, *args, **kwargs):
        denied = _domain_gate(request, kwargs["domain_code"])
        if denied is not None:
            return denied
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        if _fake(self):
            return NoDuesRequest.objects.none()
        domain_code = self.kwargs["domain_code"]
        # One filter() call: both conditions apply to the same clearance row.
        qs = NoDuesRequest.objects.filter(
            status=nodues_rules.IN_PROGRESS,
            clearances__domain_code=domain_code,
            clearances__result=nodues_rules.RESULT_PENDING,
        )
        if domain_code == "department":
            department = department_of(_uid(self.request))
            if not department:
                return NoDuesRequest.objects.none()
            qs = qs.filter(department=department)
        return qs


class NoDuesDetailView(_Gated, generics.RetrieveAPIView):
    serializer_class = s.NoDuesDetailSerializer
    permission_codes = {"GET": "oap.nodues.view_self"}

    def get_queryset(self):
        if _fake(self):
            return NoDuesRequest.objects.none()
        return NoDuesRequest.objects.filter(
            student_id=_uid(self.request)
        ).prefetch_related("clearances")


class NoDuesClearanceView(APIView):
    permission_classes = [HasModuleGrant(MODULE_CODE)]

    @extend_schema(request=s.NoDuesClearanceInputSerializer,
                   responses=s.NoDuesWithClearancesSerializer)
    def post(self, request, pk, domain_code):
        denied = _domain_gate(request, domain_code)
        if denied is not None:
            return denied
        payload = s.NoDuesClearanceInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: nodues_service.record_clearance(
                pk, domain_code, payload.validated_data["result"], _uid(request),
                payload.validated_data["remark"]),
            lambda obj: Response(s.NoDuesWithClearancesSerializer(obj).data),
        )


class NoDuesFinalizeView(_Gated, APIView):
    permission_codes = {"POST": "oap.nodues.finalize"}

    @extend_schema(request=None, responses=s.NoDuesWithClearancesSerializer)
    def post(self, request, pk):
        return _guarded(
            lambda: nodues_service.finalize_nodues(pk, _uid(request)),
            lambda obj: Response(s.NoDuesWithClearancesSerializer(obj).data),
        )


class NoDuesCertificateView(_Gated, APIView):
    permission_codes = {"GET": "oap.nodues.view_self"}

    @extend_schema(responses=s.NoDuesCertificateSerializer)
    def get(self, request, pk):
        def ok(obj):
            data = {
                "certificate_number": obj.certificate_number,
                "student_id": obj.student_id,
                "issued_on": obj.finalized_at.date() if obj.finalized_at else None,
            }
            return Response(s.NoDuesCertificateSerializer(data).data)

        return _guarded(
            lambda: nodues_service.certificate_for(pk, _uid(request)), ok
        )


# -- Assistantship -------------------------------------------------------------
class AssistantshipListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.AssistantshipSerializer
    permission_codes = {"GET": "oap.assistantship.view_self",
                        "POST": "oap.assistantship.submit"}

    def get_queryset(self):
        if _fake(self):
            return AssistantshipClaim.objects.none()
        return AssistantshipClaim.objects.filter(student_id=_uid(self.request))

    @extend_schema(request=s.ClaimSubmitSerializer,
                   responses={201: s.AssistantshipSerializer})
    def post(self, request, *args, **kwargs):
        payload = s.ClaimSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: assistantship_service.submit_claim(
                _uid(request), payload.validated_data["claim_period"]),
            lambda obj: Response(s.AssistantshipSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )


class AssistantshipToVerifyView(_Gated, generics.ListAPIView):
    """Claims waiting on the caller as thesis or TA supervisor."""

    serializer_class = s.AssistantshipSerializer
    permission_codes = {"GET": "oap.assistantship.verify"}

    def get_queryset(self):
        if _fake(self):
            return AssistantshipClaim.objects.none()
        uid = _uid(self.request)
        return AssistantshipClaim.objects.filter(
            Q(thesis_supervisor_id=uid) | Q(ta_supervisor_id=uid),
            status__in=(assistantship_rules.AWAITING_DUAL,
                        assistantship_rules.AWAITING_OTHER),
        )


class _AssistantshipDepartmentQueue(_Gated, generics.ListAPIView):
    """Claims in one state, limited to the caller's department."""

    serializer_class = s.AssistantshipSerializer
    queue_status = None

    def get_queryset(self):
        if _fake(self):
            return AssistantshipClaim.objects.none()
        department = department_of(_uid(self.request))
        if not department:
            return AssistantshipClaim.objects.none()
        return AssistantshipClaim.objects.filter(
            status=self.queue_status, department=department
        )


class AssistantshipReviewQueueView(_AssistantshipDepartmentQueue):
    permission_codes = {"GET": "oap.assistantship.review"}
    queue_status = assistantship_rules.AWAITING_DEPARTMENT


class AssistantshipDecisionQueueView(_AssistantshipDepartmentQueue):
    permission_codes = {"GET": "oap.assistantship.decide"}
    queue_status = assistantship_rules.AWAITING_HOD


class AssistantshipStipendQueueView(_Gated, generics.ListAPIView):
    """The Academic Administrator is institute-wide: no department filter."""

    serializer_class = s.AssistantshipSerializer
    permission_codes = {"GET": "oap.assistantship.process_stipend"}

    def get_queryset(self):
        if _fake(self):
            return AssistantshipClaim.objects.none()
        return AssistantshipClaim.objects.filter(status=assistantship_rules.APPROVED)


class AssistantshipDetailView(_Gated, generics.RetrieveAPIView):
    serializer_class = s.AssistantshipDetailSerializer
    permission_codes = {"GET": "oap.assistantship.view_self"}

    def get_queryset(self):
        if _fake(self):
            return AssistantshipClaim.objects.none()
        return AssistantshipClaim.objects.filter(student_id=_uid(self.request))


class AssistantshipVerifyView(_Gated, APIView):
    permission_codes = {"POST": "oap.assistantship.verify"}

    @extend_schema(request=s.ClaimVerifySerializer,
                   responses=s.AssistantshipSerializer)
    def post(self, request, pk):
        payload = s.ClaimVerifySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: assistantship_service.verify_claim(
                pk, payload.validated_data["role"], _uid(request),
                payload.validated_data["remark"]),
            lambda obj: Response(s.AssistantshipSerializer(obj).data),
        )


class AssistantshipForwardView(_Gated, APIView):
    permission_codes = {"POST": "oap.assistantship.review"}

    @extend_schema(request=s.RemarkSerializer, responses=s.AssistantshipSerializer)
    def post(self, request, pk):
        payload = s.RemarkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: assistantship_service.forward_claim(
                pk, _uid(request), payload.validated_data["remark"]),
            lambda obj: Response(s.AssistantshipSerializer(obj).data),
        )


class AssistantshipDecisionView(_Gated, APIView):
    permission_codes = {"POST": "oap.assistantship.decide"}

    @extend_schema(request=s.DecisionSerializer, responses=s.AssistantshipSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: assistantship_service.decide_claim(
                pk, payload.validated_data["action"], _uid(request),
                payload.validated_data["remark"]),
            lambda obj: Response(s.AssistantshipSerializer(obj).data),
        )


class AssistantshipStipendView(_Gated, APIView):
    permission_codes = {"POST": "oap.assistantship.process_stipend"}

    @extend_schema(request=s.RemarkSerializer, responses=s.AssistantshipSerializer)
    def post(self, request, pk):
        payload = s.RemarkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _guarded(
            lambda: assistantship_service.process_stipend(
                pk, _uid(request), payload.validated_data["remark"]),
            lambda obj: Response(s.AssistantshipSerializer(obj).data),
        )


# -- Records -------------------------------------------------------------------
class SupervisorAssignmentListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.SupervisorAssignmentSerializer
    permission_codes = {"GET": "oap.assignment.manage",
                        "POST": "oap.assignment.manage"}

    def get_queryset(self):
        return SupervisorAssignment.objects.order_by("-created_at", "-id")

    @extend_schema(request=s.SupervisorAssignmentWriteSerializer,
                   responses={201: s.SupervisorAssignmentSerializer})
    def post(self, request, *args, **kwargs):
        payload = s.SupervisorAssignmentWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        return _guarded(
            lambda: records_service.record_supervisor(
                data["student_id"], data["faculty_id"], _uid(request),
                data["decision_reference"]),
            lambda obj: Response(s.SupervisorAssignmentSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )


class TAAssignmentListView(_Gated, generics.ListCreateAPIView):
    serializer_class = s.TAAssignmentSerializer
    permission_codes = {"GET": "oap.assignment.manage",
                        "POST": "oap.assignment.manage"}

    def get_queryset(self):
        return TAAssignment.objects.order_by("-created_at", "-id")

    @extend_schema(request=s.TAAssignmentWriteSerializer,
                   responses={201: s.TAAssignmentSerializer})
    def post(self, request, *args, **kwargs):
        payload = s.TAAssignmentWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        return _guarded(
            lambda: records_service.record_ta(
                data["student_id"], _uid(request), data["course_code"],
                data["faculty_id"]),
            lambda obj: Response(s.TAAssignmentSerializer(obj).data,
                                 status=status.HTTP_201_CREATED),
        )
