"""DRF views for Department module.

Fail-closed authorization:
- MODULE = HasModuleGrant("department") gates module access.
- Fine-grained HasPermission(...) gates individual endpoints.
- Selectors scope querysets to what the caller may touch.
"""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission

from modules.department.api import serializers as s
from modules.department.selectors import seminar as selectors
from modules.department.services import seminar_service, allocation_service

MODULE = HasModuleGrant("department")


def _actor(request):
    return getattr(request, "principal", None)


class SeminarRequestListCreateView(generics.ListCreateAPIView):
    """List seminar requests visible to caller, or submit a new seminar request (OA-UC-51)."""
    permission_classes = [MODULE]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.SeminarRequestCreateSerializer
        return s.SeminarRequestSerializer

    def get_queryset(self):
        return selectors.visible_seminar_requests(_actor(self.request))

    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        # Enforce submit permission
        HasPermission("department.seminar.request")().has_permission(request, self)

        payload = s.SeminarRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = seminar_service.submit_seminar_request(
            actor=_actor(request),
            topic=data["topic"],
            abstract=data["abstract"],
            programme=data.get("programme", "M.Tech"),
            department=data.get("department", ""),
            preferred_date=data.get("preferred_date"),
            faculty_advisor_id=data.get("faculty_advisor_id"),
            faculty_advisor_name=data.get("faculty_advisor_name", ""),
        )
        return Response(s.SeminarRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class SeminarRequestDetailView(APIView):
    """Detail view or cancellation of a graduate seminar request."""
    permission_classes = [MODULE]

    def _get_request(self, pk: int):
        req = selectors.visible_seminar_requests(_actor(self.request)).filter(pk=pk).first()
        if not req:
            raise NotFoundError(f"Seminar request #{pk} not found.", code="not_found")
        return req

    def get(self, request, pk: int):
        HasPermission("department.seminar.view_self")().has_permission(request, self)
        req = self._get_request(pk)
        return Response(s.SeminarRequestSerializer(req).data)

    def delete(self, request, pk: int):
        HasPermission("department.seminar.request")().has_permission(request, self)
        req = seminar_service.cancel_seminar_request(_actor(request), pk)
        return Response(s.SeminarRequestSerializer(req).data)


class PendingSeminarsListView(generics.ListAPIView):
    """Queue of seminar requests in AWAITING_SCHEDULING status (OA-UC-53)."""
    permission_classes = [MODULE, HasPermission("department.seminar.schedule")]
    serializer_class = s.SeminarRequestSerializer

    def get_queryset(self):
        return selectors.pending_seminar_requests(_actor(self.request))


class ScheduleSeminarView(APIView):
    """Department Administrator schedules a pending graduate seminar (OA-UC-53, OA-BR-62)."""
    permission_classes = [MODULE, HasPermission("department.seminar.schedule")]

    def post(self, request, pk: int):
        payload = s.GraduateSeminarScheduleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        seminar = seminar_service.schedule_graduate_seminar(
            actor=_actor(request),
            request_id=pk,
            scheduled_date=data["scheduled_date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            venue=data["venue"],
            session_chair=data.get("session_chair", ""),
            remarks=data.get("remarks", ""),
        )
        return Response(s.GraduateSeminarSerializer(seminar).data, status=status.HTTP_201_CREATED)


class RejectSeminarView(APIView):
    """Department Administrator rejects a seminar request."""
    permission_classes = [MODULE, HasPermission("department.seminar.schedule")]

    def post(self, request, pk: int):
        payload = s.SeminarRejectSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = seminar_service.reject_seminar_request(
            actor=_actor(request),
            request_id=pk,
            reason=data["reason"],
        )
        return Response(s.SeminarRequestSerializer(req).data)


class ScheduledSeminarListView(generics.ListAPIView):
    """Scheduled graduate seminars viewable by students and faculty (AFR-OAP-049)."""
    permission_classes = [MODULE, HasPermission("department.seminar.view")]
    serializer_class = s.GraduateSeminarSerializer

    def get_queryset(self):
        dept = self.request.query_params.get("department", "")
        return selectors.scheduled_seminars(department=dept)


class ScheduledSeminarDetailView(generics.RetrieveAPIView):
    """Detail of a single scheduled seminar with history logs."""
    permission_classes = [MODULE, HasPermission("department.seminar.view")]
    serializer_class = s.GraduateSeminarSerializer
    queryset = selectors.scheduled_seminars()


class TAAllocationListCreateView(generics.ListCreateAPIView):
    """List or create TA allocations (AFR-OAP-044)."""
    permission_classes = [MODULE]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.TAAllocationCreateSerializer
        return s.TAAllocationSerializer

    def get_queryset(self):
        HasPermission("department.allocation.view")().has_permission(self.request, self)
        return selectors.visible_ta_allocations(_actor(self.request))

    def create(self, request, *args, **kwargs):
        HasPermission("department.allocation.manage")().has_permission(request, self)
        payload = s.TAAllocationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        alloc = allocation_service.allocate_teaching_assistant(
            actor=_actor(request),
            student_id=data["student_id"],
            student_name=data["student_name"],
            course_code=data["course_code"],
            course_name=data["course_name"],
            faculty_id=data.get("faculty_id"),
            faculty_name=data.get("faculty_name", ""),
            programme=data.get("programme", "M.Tech"),
            semester=data.get("semester", "Monsoon"),
            academic_year=data.get("academic_year", "2026-27"),
            hours_per_week=data.get("hours_per_week", 8),
            department=data.get("department", ""),
        )
        return Response(s.TAAllocationSerializer(alloc).data, status=status.HTTP_201_CREATED)


class SupervisorAllocationListCreateView(generics.ListCreateAPIView):
    """List or create thesis supervisor allocations (AFR-OAP-043)."""
    permission_classes = [MODULE]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.ThesisSupervisorAllocationCreateSerializer
        return s.ThesisSupervisorAllocationSerializer

    def get_queryset(self):
        HasPermission("department.allocation.view")().has_permission(self.request, self)
        return selectors.visible_supervisor_allocations(_actor(self.request))

    def create(self, request, *args, **kwargs):
        HasPermission("department.allocation.manage")().has_permission(request, self)
        payload = s.ThesisSupervisorAllocationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        alloc = allocation_service.allocate_thesis_supervisor(
            actor=_actor(request),
            student_id=data["student_id"],
            student_name=data["student_name"],
            programme=data.get("programme", "M.Tech"),
            supervisor_id=data["supervisor_id"],
            supervisor_name=data["supervisor_name"],
            co_supervisor_name=data.get("co_supervisor_name", ""),
            thesis_topic=data.get("thesis_topic", ""),
            academic_year=data.get("academic_year", "2026-27"),
            department=data.get("department", ""),
        )
        return Response(s.ThesisSupervisorAllocationSerializer(alloc).data, status=status.HTTP_201_CREATED)


class AnnouncementListCreateView(generics.ListCreateAPIView):
    """List or publish department announcements."""
    permission_classes = [MODULE]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.DepartmentAnnouncementCreateSerializer
        return s.DepartmentAnnouncementSerializer

    def get_queryset(self):
        HasPermission("department.announcement.view")().has_permission(self.request, self)
        return selectors.published_announcements()

    def create(self, request, *args, **kwargs):
        HasPermission("department.announcement.publish")().has_permission(request, self)
        payload = s.DepartmentAnnouncementCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        ann = allocation_service.create_announcement(
            actor=_actor(request),
            title=data["title"],
            content=data["content"],
            department=data.get("department", ""),
            target_audience=data.get("target_audience", "ALL"),
            is_pinned=data.get("is_pinned", False),
        )
        return Response(s.DepartmentAnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)
