"""Views for Hostel Management module.

Strictly follows two gates: module grant, then specific permission.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hostel.api.serializers import (
    AccommodationRequestSerializer,
    HostelComplaintSerializer,
    HostelFineSerializer,
    HostelNoticeSerializer,
    HostelSerializer,
    LeaveRequestSerializer,
    StudentAttendanceSerializer,
)
from modules.hostel.selectors.scoping import (
    visible_accommodations,
    visible_complaints,
    visible_fines,
    visible_hostels,
    visible_leaves,
    visible_notices,
)
from modules.hostel.services.accommodations import (
    submit_accommodation_request,
)
from modules.hostel.services.operations import (
    impose_fine,
    process_complaint_decision,
    process_leave_decision,
    publish_notice,
    record_student_attendance,
    submit_complaint,
    submit_leave_request,
)


class HostelListView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.room.view")]
    serializer_class = HostelSerializer

    @extend_schema(summary="List visible hostels", responses={200: HostelSerializer(many=True)})
    def get(self, request):
        role = getattr(request.user, "active_role", "")
        qs = visible_hostels(request.user, role)
        serializer = HostelSerializer(qs, many=True)
        return Response(serializer.data)


class AccommodationListCreateView(APIView):
    permission_classes = [
        HasModuleGrant("hostel"),
        HasPermission("hostel.accommodation.view"),
    ]
    serializer_class = AccommodationRequestSerializer

    @extend_schema(
        summary="List accommodations",
        responses={200: AccommodationRequestSerializer(many=True)},
    )
    def get(self, request):
        role = getattr(request.user, "active_role", "")
        qs = visible_accommodations(request.user, role)
        serializer = AccommodationRequestSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Submit accommodation request",
        request=AccommodationRequestSerializer,
        responses={201: AccommodationRequestSerializer},
    )
    def post(self, request):
        preferred_hostel = request.data.get("preferred_hostel")
        academic_year = request.data.get("academic_year", "2026-2027")
        remarks = request.data.get("remarks", "")
        obj = submit_accommodation_request(
            user_id=request.user.id,
            preferred_hostel_id=preferred_hostel,
            academic_year=academic_year,
            remarks=remarks,
        )
        return Response(AccommodationRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class LeaveListCreateView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.leave.view")]
    serializer_class = LeaveRequestSerializer

    @extend_schema(summary="List leaves", responses={200: LeaveRequestSerializer(many=True)})
    def get(self, request):
        role = getattr(request.user, "active_role", "")
        qs = visible_leaves(request.user, role)
        return Response(LeaveRequestSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit leave request",
        request=LeaveRequestSerializer,
        responses={201: LeaveRequestSerializer},
    )
    def post(self, request):
        obj = submit_leave_request(
            user_id=request.user.id,
            hostel_id=request.data.get("hostel"),
            start_date=request.data.get("start_date"),
            end_date=request.data.get("end_date"),
            reason=request.data.get("reason", ""),
        )
        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class LeaveActionView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.leave.review")]
    serializer_class = LeaveRequestSerializer

    @extend_schema(summary="Approve or reject leave", responses={200: LeaveRequestSerializer})
    def post(self, request, pk: int):
        event = request.data.get("event")
        role = getattr(request.user, "active_role", "caretaker")
        remarks = request.data.get("remarks", "")
        obj = process_leave_decision(
            leave_id=pk,
            event=event,
            role=role,
            action_by_user_id=request.user.id,
            remarks=remarks,
        )
        return Response(LeaveRequestSerializer(obj).data)


class ComplaintListCreateView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.complaint.view")]
    serializer_class = HostelComplaintSerializer

    @extend_schema(summary="List complaints", responses={200: HostelComplaintSerializer(many=True)})
    def get(self, request):
        role = getattr(request.user, "active_role", "")
        qs = visible_complaints(request.user, role)
        return Response(HostelComplaintSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit complaint",
        request=HostelComplaintSerializer,
        responses={201: HostelComplaintSerializer},
    )
    def post(self, request):
        obj = submit_complaint(
            user_id=request.user.id,
            hostel_id=request.data.get("hostel"),
            category=request.data.get("category", "General"),
            title=request.data.get("title", ""),
            description=request.data.get("description", ""),
        )
        return Response(HostelComplaintSerializer(obj).data, status=status.HTTP_201_CREATED)


class ComplaintActionView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.complaint.review")]
    serializer_class = HostelComplaintSerializer

    @extend_schema(summary="Take action on complaint", responses={200: HostelComplaintSerializer})
    def post(self, request, pk: int):
        event = request.data.get("event")
        role = getattr(request.user, "active_role", "caretaker")
        remarks = request.data.get("remarks", "")
        obj = process_complaint_decision(
            complaint_id=pk,
            event=event,
            role=role,
            remarks=remarks,
        )
        return Response(HostelComplaintSerializer(obj).data)


class AttendanceCreateView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.attendance.create")]
    serializer_class = StudentAttendanceSerializer

    @extend_schema(
        summary="Record attendance",
        request=StudentAttendanceSerializer,
        responses={200: StudentAttendanceSerializer},
    )
    def post(self, request):
        obj = record_student_attendance(
            user_id=request.data.get("user_id"),
            hostel_id=request.data.get("hostel"),
            date=request.data.get("date"),
            status=request.data.get("status", "PRESENT"),
            marked_by_user_id=request.user.id,
        )
        return Response(StudentAttendanceSerializer(obj).data)


class FineListCreateView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.fine.view")]
    serializer_class = HostelFineSerializer

    @extend_schema(summary="List fines", responses={200: HostelFineSerializer(many=True)})
    def get(self, request):
        role = getattr(request.user, "active_role", "")
        qs = visible_fines(request.user, role)
        return Response(HostelFineSerializer(qs, many=True).data)

    @extend_schema(
        summary="Impose fine",
        request=HostelFineSerializer,
        responses={201: HostelFineSerializer},
    )
    def post(self, request):
        obj = impose_fine(
            user_id=request.data.get("user_id"),
            hostel_id=request.data.get("hostel"),
            amount=float(request.data.get("amount", 0)),
            reason=request.data.get("reason", ""),
            imposed_by_user_id=request.user.id,
        )
        return Response(HostelFineSerializer(obj).data, status=status.HTTP_201_CREATED)


class NoticeListCreateView(APIView):
    permission_classes = [HasModuleGrant("hostel"), HasPermission("hostel.notice.view")]
    serializer_class = HostelNoticeSerializer

    @extend_schema(summary="List notices", responses={200: HostelNoticeSerializer(many=True)})
    def get(self, request):
        role = getattr(request.user, "active_role", "")
        qs = visible_notices(request.user, role)
        return Response(HostelNoticeSerializer(qs, many=True).data)

    @extend_schema(
        summary="Publish notice",
        request=HostelNoticeSerializer,
        responses={201: HostelNoticeSerializer},
    )
    def post(self, request):
        role = getattr(request.user, "active_role", "caretaker")
        obj = publish_notice(
            hostel_id=request.data.get("hostel"),
            title=request.data.get("title", ""),
            body=request.data.get("body", ""),
            topic=request.data.get("topic", "general"),
            published_by_user_id=request.user.id,
            published_by_role=role,
        )
        return Response(HostelNoticeSerializer(obj).data, status=status.HTTP_201_CREATED)
