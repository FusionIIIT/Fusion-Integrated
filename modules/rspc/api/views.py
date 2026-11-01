"""RSPC API views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasPermission, HasModuleGrant
from modules.rspc import selectors, services
from modules.rspc.api.serializers import (
    ResearchProjectSerializer, WriteResearchProjectSerializer,
    ResearchProjectTransitionSerializer, TransitionRequestSerializer,
    ConsultancyProjectSerializer, WriteConsultancySerializer,
    StaffAppointmentSerializer, WriteStaffAppointmentSerializer,
    FinanceRequestSerializer, WriteFinanceRequestSerializer,
    ProcurementRequestSerializer, WriteProcurementSerializer,
    ProgressReportSerializer, WriteProgressReportSerializer,
    ProjectClosureSerializer, WriteProjectClosureSerializer,
)
from modules.rspc.models import (
    ResearchProject, ConsultancyProject, StaffAppointment,
    FinanceRequest, ProcurementRequest, ProgressReport, ProjectClosure,
    ResearchProjectTransition, ConsultancyTransition,
    AppointmentTransition, FinanceTransition,
    ProcurementTransition, ProgressReportTransition, ClosureTransition,
)


def _actor(request):
    return getattr(request, "principal", None)


# ---------------------------------------------------------------------------
# Helper: map domain errors to DRF responses
# ---------------------------------------------------------------------------

def _handle_domain_error(exc) -> Response:
    from modules.rspc.domain.state_machine import (
        InvalidTransition, ActorNotAllowed, GuardFailed,
    )
    if isinstance(exc, InvalidTransition):
        return Response(
            {"detail": str(exc), "code": "invalid_transition"},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, ActorNotAllowed):
        return Response(
            {"detail": str(exc), "code": "actor_not_allowed"},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, GuardFailed):
        return Response(
            {"detail": str(exc), "code": f"guard_failed.{exc.guard}"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    raise exc


# ===========================================================================
# Research Project Proposals
# ===========================================================================

class ProposalListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.proposal.view_self", "rspc.proposal.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ResearchProject.objects.none()
        return selectors.visible_proposals(actor)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return WriteResearchProjectSerializer
        return ResearchProjectSerializer

    @extend_schema(summary="List research project proposals", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Create a research project proposal draft", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteResearchProjectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = services.create_proposal(
            principal=request.principal, **ser.validated_data)
        return Response(ResearchProjectSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class ProposalDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.proposal.view_self", "rspc.proposal.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ResearchProject.objects.none()
        return selectors.visible_proposals(actor)

    def get_serializer_class(self):
        return (WriteResearchProjectSerializer
                if self.request.method in ("PUT", "PATCH")
                else ResearchProjectSerializer)

    @extend_schema(summary="Update proposal draft", tags=["rspc"])
    def patch(self, request, pk, *a, **kw):
        ser = WriteResearchProjectSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.update_proposal(
                proposal_id=pk, principal=request.principal,
                **ser.validated_data)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(ResearchProjectSerializer(obj).data)


class ProposalTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a proposal to a new state",
        request=TransitionRequestSerializer,
        responses=ResearchProjectSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_proposal(
                proposal_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(ResearchProjectSerializer(obj).data)


class ProposalHistoryView(generics.ListAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.proposal.view_self", "rspc.proposal.view"),
    ]
    serializer_class = ResearchProjectTransitionSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ResearchProjectTransition.objects.none()
        pk = self.kwargs.get("pk")
        proposal = selectors.get_proposal(pk, actor) if pk else None
        if proposal is None:
            return ResearchProjectTransition.objects.none()
        return proposal.transitions.order_by("at")


# ===========================================================================
# Consultancy Projects
# ===========================================================================

class ConsultancyListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.consultancy.view_self", "rspc.consultancy.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ConsultancyProject.objects.none()
        return selectors.visible_consultancy(actor)

    def get_serializer_class(self):
        return (WriteConsultancySerializer
                if self.request.method == "POST"
                else ConsultancyProjectSerializer)

    @extend_schema(summary="List consultancy projects", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Register a new consultancy project", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteConsultancySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = services.create_consultancy(
            principal=request.principal, **ser.validated_data)
        return Response(ConsultancyProjectSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class ConsultancyTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a consultancy project",
        request=TransitionRequestSerializer,
        responses=ConsultancyProjectSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_consultancy(
                project_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(ConsultancyProjectSerializer(obj).data)


# ===========================================================================
# Staff Appointments
# ===========================================================================

class AppointmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.appointment.view_self", "rspc.appointment.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return StaffAppointment.objects.none()
        return selectors.visible_appointments(actor)

    def get_serializer_class(self):
        return (WriteStaffAppointmentSerializer
                if self.request.method == "POST"
                else StaffAppointmentSerializer)

    @extend_schema(summary="List staff appointment requests", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Submit staff appointment request", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteStaffAppointmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = services.create_appointment(
            principal=request.principal, **ser.validated_data)
        return Response(StaffAppointmentSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class AppointmentTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a staff appointment request",
        request=TransitionRequestSerializer,
        responses=StaffAppointmentSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_appointment(
                appointment_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(StaffAppointmentSerializer(obj).data)


# ===========================================================================
# Financial Requests
# ===========================================================================

class FinanceListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.finance.view_self", "rspc.finance.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return FinanceRequest.objects.none()
        return selectors.visible_finance(actor)

    def get_serializer_class(self):
        return (WriteFinanceRequestSerializer
                if self.request.method == "POST"
                else FinanceRequestSerializer)

    @extend_schema(summary="List financial / fund requests", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Submit a financial request", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteFinanceRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = services.create_finance_request(
            principal=request.principal, **ser.validated_data)
        return Response(FinanceRequestSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class FinanceTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a financial request",
        request=TransitionRequestSerializer,
        responses=FinanceRequestSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_finance(
                request_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(FinanceRequestSerializer(obj).data)


# ===========================================================================
# Procurement Requests
# ===========================================================================

class ProcurementListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.procurement.view_self", "rspc.procurement.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ProcurementRequest.objects.none()
        return selectors.visible_procurement(actor)

    def get_serializer_class(self):
        return (WriteProcurementSerializer
                if self.request.method == "POST"
                else ProcurementRequestSerializer)

    @extend_schema(summary="List procurement requests", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Submit a procurement request", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteProcurementSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = services.create_procurement_request(
            principal=request.principal, **ser.validated_data)
        return Response(ProcurementRequestSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class ProcurementTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a procurement request",
        request=TransitionRequestSerializer,
        responses=ProcurementRequestSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_procurement(
                request_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(ProcurementRequestSerializer(obj).data)


# ===========================================================================
# Progress Reports
# ===========================================================================

class ProgressReportListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.progress_report.view_self",
                      "rspc.progress_report.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ProgressReport.objects.none()
        return selectors.visible_progress_reports(actor)

    def get_serializer_class(self):
        return (WriteProgressReportSerializer
                if self.request.method == "POST"
                else ProgressReportSerializer)

    @extend_schema(summary="List progress reports", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Create a progress report draft", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteProgressReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project_id = ser.validated_data.pop("project_id")
        obj = services.create_progress_report(
            principal=request.principal,
            project_id=project_id,
            **ser.validated_data)
        return Response(ProgressReportSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class ProgressReportTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a progress report",
        request=TransitionRequestSerializer,
        responses=ProgressReportSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_progress_report(
                report_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(ProgressReportSerializer(obj).data)


# ===========================================================================
# Project Closures
# ===========================================================================

class ClosureListCreateView(generics.ListCreateAPIView):
    permission_classes = [
        HasModuleGrant("rspc"),
        HasPermission("rspc.closure.view_self", "rspc.closure.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        if actor is None or getattr(self, "swagger_fake_view", False):
            return ProjectClosure.objects.none()
        return selectors.visible_closures(actor)

    def get_serializer_class(self):
        return (WriteProjectClosureSerializer
                if self.request.method == "POST"
                else ProjectClosureSerializer)

    @extend_schema(summary="List project closures", tags=["rspc"])
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Submit a project closure record", tags=["rspc"])
    def post(self, request, *a, **kw):
        ser = WriteProjectClosureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project_id = ser.validated_data.pop("project_id")
        obj = services.create_closure(
            principal=request.principal,
            project_id=project_id,
            **ser.validated_data)
        return Response(ProjectClosureSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class ClosureTransitionView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="Transition a project closure record",
        request=TransitionRequestSerializer,
        responses=ProjectClosureSerializer,
        tags=["rspc"],
    )
    def post(self, request, pk):
        ser = TransitionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = services.transition_closure(
                closure_id=pk,
                to_status=ser.validated_data["to_status"],
                principal=request.principal,
                remarks=ser.validated_data.get("remarks", ""),
            )
        except (NotFoundError,) as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return _handle_domain_error(exc)
        return Response(ProjectClosureSerializer(obj).data)


# ===========================================================================
# Dashboard / Summary
# ===========================================================================

class DashboardView(APIView):
    permission_classes = [HasModuleGrant("rspc")]

    @extend_schema(
        summary="RSPC module dashboard summary",
        responses={200: dict},
        tags=["rspc"],
    )
    def get(self, request):
        p = request.principal
        data: dict = {}
        if p.has_permission("rspc.proposal.view_self") or p.has_permission("rspc.proposal.view"):
            data["proposals"] = selectors.visible_proposals(p).count()
        if p.has_permission("rspc.consultancy.view_self") or p.has_permission("rspc.consultancy.view"):
            data["consultancy"] = selectors.visible_consultancy(p).count()
        if p.has_permission("rspc.finance.view_self") or p.has_permission("rspc.finance.view"):
            data["finance_requests"] = selectors.visible_finance(p).count()
        if p.has_permission("rspc.procurement.view_self") or p.has_permission("rspc.procurement.view"):
            data["procurement_requests"] = selectors.visible_procurement(p).count()
        if p.has_permission("rspc.progress_report.view_self") or p.has_permission("rspc.progress_report.view"):
            data["progress_reports"] = selectors.visible_progress_reports(p).count()
        return Response(data)
