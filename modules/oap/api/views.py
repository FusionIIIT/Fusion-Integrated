"""Transport only: parse, delegate, serialise.

Every endpoint passes two gates: the module grant first, then the permission
for the method. Collections read and write on one path, so their permissions
are chosen per method.
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.oap.api import serializers as s
from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    LeaveApplication,
    Notification,
    SeminarRequest,
    SeminarSchedule,
    TAAssignment,
    ThesisSupervisorAssignment,
)
from modules.oap.selectors import reads, scoping
from modules.oap.services import assignments, assistantship, bonafide, leave, no_dues
from modules.oap.services import seminar as seminar_service

MODULE = HasModuleGrant("oap")


def _principal(request):
    return getattr(request, "principal", None)


class _MethodGated:
    read_codes: tuple[str, ...] = ()
    write_codes: tuple[str, ...] = ()

    def get_permissions(self):
        codes = self.read_codes if self.request.method in SAFE_METHODS else self.write_codes
        return [MODULE(), HasPermission(*codes)()]


# -- leave ---------------------------------------------------------------------
class LeaveCollectionView(_MethodGated, generics.ListCreateAPIView):
    queryset = LeaveApplication.objects.none()
    serializer_class = s.LeaveSerializer
    read_codes = ("oap.leave_application.view_self", "oap.leave_application.view")
    write_codes = ("oap.leave_application.create",)

    def get_queryset(self):
        return scoping.leave_for(_principal(self.request))

    def create(self, request, *args, **kwargs):
        body = s.LeaveCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        app = leave.submit(_principal(request), **body.validated_data)
        return Response(s.LeaveSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveDetailView(generics.RetrieveAPIView):
    queryset = LeaveApplication.objects.none()
    serializer_class = s.LeaveSerializer
    permission_classes = [
        MODULE,
        HasPermission("oap.leave_application.view_self", "oap.leave_application.view"),
    ]

    def get_queryset(self):
        return scoping.leave_for(_principal(self.request))


class LeaveDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("oap.leave_application.approve")]

    @extend_schema(request=s.OutcomeSerializer, responses=s.LeaveSerializer)
    def post(self, request, pk: int):
        body = s.OutcomeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        app = leave.decide(_principal(request), pk, body.validated_data["outcome"])
        return Response(s.LeaveSerializer(app).data)


# -- bonafide ------------------------------------------------------------------
class BonafideCollectionView(_MethodGated, generics.ListCreateAPIView):
    queryset = BonafideRequest.objects.none()
    serializer_class = s.BonafideSerializer
    read_codes = ("oap.bonafide_request.view_self", "oap.bonafide_request.view")
    write_codes = ("oap.bonafide_request.create",)

    def get_queryset(self):
        return scoping.bonafide_for(_principal(self.request))

    def create(self, request, *args, **kwargs):
        body = s.BonafideCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        req = bonafide.request(_principal(request), **body.validated_data)
        return Response(s.BonafideSerializer(req).data, status=status.HTTP_201_CREATED)


class BonafideDetailView(generics.RetrieveAPIView):
    queryset = BonafideRequest.objects.none()
    serializer_class = s.BonafideSerializer
    permission_classes = [
        MODULE,
        HasPermission("oap.bonafide_request.view_self", "oap.bonafide_request.view"),
    ]

    def get_queryset(self):
        return scoping.bonafide_for(_principal(self.request))


class BonafideVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("oap.bonafide_request.review")]

    @extend_schema(request=None, responses=s.BonafideSerializer)
    def post(self, request, pk: int):
        return Response(s.BonafideSerializer(bonafide.verify(_principal(request), pk)).data)


class BonafideDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("oap.bonafide_request.approve")]

    @extend_schema(request=s.OutcomeSerializer, responses=s.BonafideSerializer)
    def post(self, request, pk: int):
        body = s.OutcomeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        req = bonafide.decide(_principal(request), pk, body.validated_data["outcome"])
        return Response(s.BonafideSerializer(req).data)


class BonafideCertificateView(APIView):
    permission_classes = [MODULE, HasPermission("oap.bonafide_certificate.view_self")]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def get(self, request, pk: int):
        req = reads.bonafide_certificate_for(_principal(request), pk)
        return Response({"request_id": req.pk, "available": True, "approved_at": req.decided_at})


# -- no-dues -------------------------------------------------------------------
class NoDuesCollectionView(_MethodGated, APIView):
    read_codes = ("oap.no_dues_case.view_self", "oap.no_dues_case.view")
    write_codes = ("oap.no_dues_case.create",)

    @extend_schema(
        operation_id="oap_no_dues_cases_list", request=None, responses=OpenApiTypes.OBJECT
    )
    def get(self, request):
        principal = _principal(request)
        rows = [
            {"id": c.pk, "finalized": c.finalized, **reads.no_dues_view_for(principal, c)}
            for c in scoping.no_dues_for(principal)
        ]
        return Response(rows)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        case = no_dues.initiate(_principal(request))
        return Response({"id": case.pk, "status": "in_progress"}, status=status.HTTP_201_CREATED)


class NoDuesDetailView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("oap.no_dues_case.view_self", "oap.no_dues_case.view"),
    ]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def get(self, request, pk: int):
        principal = _principal(request)
        case = scoping.no_dues_for(principal).filter(pk=pk).first()
        if case is None:
            raise NotFoundError("No-dues case not found.", code="not_found")
        return Response(
            {"id": case.pk, "finalized": case.finalized, **reads.no_dues_view_for(principal, case)}
        )


class NoDuesResultView(APIView):
    permission_classes = [MODULE, HasPermission("oap.no_dues_result.update")]

    @extend_schema(request=s.NoDuesResultSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk: int):
        body = s.NoDuesResultSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        principal = _principal(request)
        case = no_dues.record_result(principal, pk, body.validated_data["result"])
        return Response(
            {"id": case.pk, "finalized": case.finalized, **reads.no_dues_view_for(principal, case)}
        )


class NoDuesFinalizeView(APIView):
    permission_classes = [MODULE, HasPermission("oap.no_dues_case.approve")]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk: int):
        case = no_dues.finalize(_principal(request), pk)
        return Response({"id": case.pk, "finalized": case.finalized})


class NoDuesCertificateView(APIView):
    permission_classes = [MODULE, HasPermission("oap.no_dues_certificate.view_self")]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def get(self, request, pk: int):
        case = reads.no_dues_certificate_for(_principal(request), pk)
        return Response({"case_id": case.pk, "available": True, "finalized_at": case.finalized_at})


# -- assistantship -------------------------------------------------------------
_CLAIM_READ = (
    "oap.assistantship_claim.view_self",
    "oap.assistantship_claim.view",
    "oap.assistantship_verification.review",
)


class ClaimCollectionView(_MethodGated, generics.ListCreateAPIView):
    queryset = AssistantshipClaim.objects.none()
    serializer_class = s.ClaimSerializer
    read_codes = _CLAIM_READ
    write_codes = ("oap.assistantship_claim.create",)

    def get_queryset(self):
        return scoping.claims_for(_principal(self.request)).prefetch_related("verifications")

    def create(self, request, *args, **kwargs):
        claim = assistantship.submit(_principal(request))
        return Response(s.ClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class ClaimDetailView(generics.RetrieveAPIView):
    queryset = AssistantshipClaim.objects.none()
    serializer_class = s.ClaimSerializer
    permission_classes = [MODULE, HasPermission(*_CLAIM_READ)]

    def get_queryset(self):
        return scoping.claims_for(_principal(self.request)).prefetch_related("verifications")


class ClaimVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("oap.assistantship_verification.review")]

    @extend_schema(request=s.VerifyClaimSerializer, responses=s.ClaimSerializer)
    def post(self, request, pk: int):
        body = s.VerifyClaimSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        claim = assistantship.verify(_principal(request), pk, body.validated_data["role"])
        return Response(s.ClaimSerializer(claim).data)


class ClaimForwardView(APIView):
    permission_classes = [MODULE, HasPermission("oap.assistantship_claim.review")]

    @extend_schema(request=None, responses=s.ClaimSerializer)
    def post(self, request, pk: int):
        return Response(s.ClaimSerializer(assistantship.forward(_principal(request), pk)).data)


class ClaimDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("oap.assistantship_claim.approve")]

    @extend_schema(request=s.OutcomeSerializer, responses=s.ClaimSerializer)
    def post(self, request, pk: int):
        body = s.OutcomeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        claim = assistantship.decide(_principal(request), pk, body.validated_data["outcome"])
        return Response(s.ClaimSerializer(claim).data)


class ClaimStipendView(APIView):
    permission_classes = [MODULE, HasPermission("oap.assistantship_claim.update")]

    @extend_schema(request=None, responses=s.ClaimSerializer)
    def post(self, request, pk: int):
        return Response(
            s.ClaimSerializer(assistantship.process_stipend(_principal(request), pk)).data
        )


# -- assignments ---------------------------------------------------------------
class ThesisAssignmentCollectionView(_MethodGated, generics.ListCreateAPIView):
    queryset = ThesisSupervisorAssignment.objects.none()
    serializer_class = s.ThesisAssignmentSerializer
    read_codes = ("oap.thesis_supervisor_assignment.view",)
    write_codes = ("oap.thesis_supervisor_assignment.assign",)

    def get_queryset(self):
        return ThesisSupervisorAssignment.objects.all()

    def create(self, request, *args, **kwargs):
        body = s.ThesisAssignmentInputSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        row = assignments.record_thesis_supervisor(_principal(request), **body.validated_data)
        return Response(s.ThesisAssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


class TAAssignmentCollectionView(_MethodGated, generics.ListCreateAPIView):
    queryset = TAAssignment.objects.none()
    serializer_class = s.TAAssignmentSerializer
    read_codes = ("oap.ta_assignment.view",)
    write_codes = ("oap.ta_assignment.assign",)

    def get_queryset(self):
        return TAAssignment.objects.all()

    def create(self, request, *args, **kwargs):
        body = s.TAAssignmentInputSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        row = assignments.record_ta(_principal(request), **body.validated_data)
        return Response(s.TAAssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


# -- seminars ------------------------------------------------------------------
class SeminarRequestCollectionView(_MethodGated, generics.ListCreateAPIView):
    queryset = SeminarRequest.objects.none()
    serializer_class = s.SeminarRequestSerializer
    read_codes = ("oap.seminar_request.view_self", "oap.seminar_request.view")
    write_codes = ("oap.seminar_request.create",)

    def get_queryset(self):
        return scoping.seminar_requests_for(_principal(self.request))

    def create(self, request, *args, **kwargs):
        req = seminar_service.request(_principal(request))
        return Response(s.SeminarRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class SeminarScheduleView(APIView):
    permission_classes = [MODULE, HasPermission("oap.seminar_schedule.update")]

    @extend_schema(request=s.SeminarScheduleInputSerializer, responses=s.SeminarScheduleSerializer)
    def post(self, request, pk: int):
        body = s.SeminarScheduleInputSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry = seminar_service.schedule(_principal(request), pk, **body.validated_data)
        return Response(s.SeminarScheduleSerializer(entry).data, status=status.HTTP_201_CREATED)


class SeminarScheduleListView(generics.ListAPIView):
    queryset = SeminarSchedule.objects.none()
    serializer_class = s.SeminarScheduleSerializer
    permission_classes = [MODULE, HasPermission("oap.seminar_schedule.view")]

    def get_queryset(self):
        return scoping.seminar_schedules_for(_principal(self.request)).select_related("request")


# -- notifications -------------------------------------------------------------
class NotificationListView(generics.ListAPIView):
    queryset = Notification.objects.none()
    serializer_class = s.NotificationSerializer
    permission_classes = [MODULE, HasPermission("oap.notification.view_self")]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient_user_id=_principal(self.request).user_id, channel="alert"
        )
