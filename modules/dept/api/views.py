"""API views for the Department module."""

from __future__ import annotations

import datetime

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_s
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.permissions import HasPermission, IsAuthenticatedPrincipal
from modules.dept.api import serializers as s
from modules.dept.api.permissions import MODULE_GRANT as MODULE
from modules.dept.domain.exceptions import AvailabilityError, DomainError
from modules.dept.domain.exceptions import ConflictError as DomainConflictError
from modules.dept.models.announcements import Announcement
from modules.dept.selectors.announcements import list_announcements_for_principal
from modules.dept.selectors.department import (
    get_department_with_headship,
    list_pending_official_changes,
)
from modules.dept.selectors.feedback import list_feedback_for_principal
from modules.dept.selectors.inventory import (
    list_inventory_items,
    list_stock_requests_for_principal,
    list_stock_transactions,
)
from modules.dept.selectors.labs import list_lab_resources, list_role_assignments
from modules.dept.selectors.profiles import list_profiles, mask_profile_for_viewer
from modules.dept.selectors.scoping import resolve_department_code
from modules.dept.selectors.timetable import list_timetables
from modules.dept.services import announcements as announcement_service
from modules.dept.services import department as department_service
from modules.dept.services import feedback as feedback_service
from modules.dept.services import inventory as inventory_service
from modules.dept.services import labs as lab_service
from modules.dept.services import profiles as profile_service
from modules.dept.services import roles as role_service
from modules.dept.services import timetable as timetable_service


def _actor(request):
    return getattr(request, "principal", None)


class AnnouncementListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.AnnouncementSerializer

    @extend_schema(responses={200: s.AnnouncementSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.announcement.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        prog = request.query_params.get("program")
        year_str = request.query_params.get("year")
        year = int(year_str) if year_str and year_str.isdigit() else None
        qs = list_announcements_for_principal(
            dept, _actor(request), program=prog, academic_year=year
        )
        return Response(s.AnnouncementSerializer(qs, many=True).data)

    @extend_schema(request=s.AnnouncementSerializer, responses={201: s.AnnouncementSerializer})
    def post(self, request):
        if not HasPermission("dept.announcement.create")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        data = request.data
        ann = announcement_service.create_announcement(
            department_code=dept,
            author_principal=_actor(request),
            title=data.get("title", ""),
            content=data.get("content", ""),
            target_role=data.get("target_role", "ALL"),
            target_program=data.get("target_program", "ALL"),
            target_academic_year=data.get("target_academic_year"),
        )
        return Response(s.AnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


class AnnouncementDetailView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        MODULE,
        HasPermission("dept.announcement.manage"),
    ]
    serializer_class = s.AnnouncementSerializer

    @extend_schema(request=s.AnnouncementSerializer, responses={200: s.AnnouncementSerializer})
    def patch(self, request, pk):
        try:
            ann = announcement_service.update_announcement(
                announcement_id=pk,
                principal=_actor(request),
                title=request.data.get("title"),
                content=request.data.get("content"),
                status=request.data.get("status"),
            )
            return Response(s.AnnouncementSerializer(ann).data)
        except Announcement.DoesNotExist:
            raise NotFoundError("Announcement not found.") from None

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        try:
            announcement_service.update_announcement(
                announcement_id=pk,
                principal=_actor(request),
                status="DELETED",
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Announcement.DoesNotExist:
            raise NotFoundError("Announcement not found.") from None


class InventoryItemListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.InventoryItemSerializer

    @extend_schema(responses={200: s.InventoryItemSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.inventory.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        cat = request.query_params.get("category")
        qs = list_inventory_items(dept, category=cat)
        return Response(s.InventoryItemSerializer(qs, many=True).data)

    @extend_schema(request=s.InventoryItemSerializer, responses={201: s.InventoryItemSerializer})
    def post(self, request):
        if not HasPermission("dept.inventory.create")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        item = inventory_service.create_inventory_item(
            department_code=dept,
            item_code=d.get("item_code", ""),
            name=d.get("name", ""),
            category=d.get("category", "CONSUMABLE"),
            initial_quantity=int(d.get("initial_quantity", d.get("quantity", 0))),
            unit=d.get("unit", "units"),
            actor_principal=_actor(request),
        )
        return Response(s.InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InventoryItemAddStockView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.inventory.create")]
    serializer_class = s.InventoryItemSerializer

    @extend_schema(
        request=inline_serializer(
            name="AddStockRequest",
            fields={
                "quantity": drf_s.IntegerField(default=1),
                "notes": drf_s.CharField(required=False, default=""),
            },
        ),
        responses={200: s.InventoryItemSerializer},
    )
    def post(self, request, pk):
        qty = int(request.data.get("quantity", 0))
        notes = request.data.get("notes", "")
        item = inventory_service.add_stock_to_item(pk, qty, _actor(request), notes=notes)
        return Response(s.InventoryItemSerializer(item).data)


class InventoryItemTransactionsView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.inventory.view")]
    serializer_class = s.StockTransactionSerializer

    @extend_schema(responses={200: s.StockTransactionSerializer(many=True)})
    def get(self, request, pk):
        qs = list_stock_transactions(pk)
        return Response(s.StockTransactionSerializer(qs, many=True).data)


class StockRequestListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.StockRequestSerializer

    @extend_schema(responses={200: s.StockRequestSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.stock_request.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        mine = request.query_params.get("mine", "").lower() in {"1", "true"}
        st = request.query_params.get("status")
        qs = list_stock_requests_for_principal(dept, _actor(request), mine_only=mine, status=st)
        return Response(s.StockRequestSerializer(qs, many=True).data)

    @extend_schema(request=s.StockRequestSerializer, responses={201: s.StockRequestSerializer})
    def post(self, request):
        if not HasPermission("dept.stock_request.create")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        try:
            sr = inventory_service.submit_stock_request(
                department_code=dept,
                inventory_item_id=d.get("inventory_item_id", d.get("inventory_item")),
                requested_quantity=int(d.get("requested_quantity", 1)),
                purpose=d.get("purpose", ""),
                faculty_principal=_actor(request),
            )
            return Response(s.StockRequestSerializer(sr).data, status=status.HTTP_201_CREATED)
        except AvailabilityError as e:
            raise ConflictError(str(e)) from e
        except DomainError as e:
            raise BadRequestError(str(e)) from e


class StockRequestDecisionView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        MODULE,
        HasPermission("dept.stock_request.approve"),
    ]
    serializer_class = s.StockRequestSerializer

    @extend_schema(
        request=inline_serializer(
            name="StockDecisionRequest",
            fields={
                "decision": drf_s.CharField(),
                "remarks": drf_s.CharField(required=False, default=""),
            },
        ),
        responses={200: s.StockRequestSerializer},
    )
    def post(self, request, pk):
        dec = request.data.get("decision", "")
        remarks = request.data.get("remarks", "")
        try:
            sr = inventory_service.decide_stock_request(pk, dec, _actor(request), remarks=remarks)
            return Response(s.StockRequestSerializer(sr).data)
        except DomainError as e:
            raise ConflictError(str(e)) from e


class StockRequestIssueView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        MODULE,
        HasPermission("dept.stock_request.issue"),
    ]
    serializer_class = s.StockRequestSerializer

    @extend_schema(
        request=inline_serializer(
            name="StockIssueRequest",
            fields={
                "notes": drf_s.CharField(required=False, default=""),
            },
        ),
        responses={200: s.StockRequestSerializer},
    )
    def post(self, request, pk):
        notes = request.data.get("notes", "")
        try:
            sr = inventory_service.issue_stock_request(pk, _actor(request), notes=notes)
            return Response(s.StockRequestSerializer(sr).data)
        except AvailabilityError as e:
            raise ConflictError(str(e)) from e
        except DomainError as e:
            raise ConflictError(str(e)) from e


class FeedbackListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.FeedbackSerializer

    @extend_schema(responses={200: s.FeedbackSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.feedback.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        mine = request.query_params.get("mine", "").lower() in {"1", "true"}
        st = request.query_params.get("status")
        qs = list_feedback_for_principal(dept, _actor(request), mine_only=mine, status=st)
        return Response(s.FeedbackSerializer(qs, many=True).data)

    @extend_schema(request=s.FeedbackSerializer, responses={201: s.FeedbackSerializer})
    def post(self, request):
        if not HasPermission("dept.feedback.create")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        try:
            fb = feedback_service.submit_feedback(
                department_code=dept,
                submitter_principal=_actor(request),
                category=d.get("category", "ACADEMIC"),
                title=d.get("title", ""),
                description=d.get("description", ""),
            )
            return Response(s.FeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)
        except DomainError as e:
            raise BadRequestError(str(e)) from e


class FeedbackReviewView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.feedback.review")]
    serializer_class = s.FeedbackSerializer

    @extend_schema(
        request=inline_serializer(
            name="FeedbackReviewRequest",
            fields={
                "admin_remarks": drf_s.CharField(required=False, default=""),
            },
        ),
        responses={200: s.FeedbackSerializer},
    )
    def post(self, request, pk):
        remarks = request.data.get("admin_remarks", "")
        try:
            fb = feedback_service.review_feedback_initial(
                pk, _actor(request), admin_remarks=remarks
            )
            return Response(s.FeedbackSerializer(fb).data)
        except DomainError as e:
            raise ConflictError(str(e)) from e


class FeedbackResolveView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.feedback.resolve")]
    serializer_class = s.FeedbackSerializer

    @extend_schema(
        request=inline_serializer(
            name="FeedbackResolveRequest",
            fields={
                "action": drf_s.CharField(default="RESOLVE"),
                "remarks": drf_s.CharField(required=False, default=""),
            },
        ),
        responses={200: s.FeedbackSerializer},
    )
    def post(self, request, pk):
        act = request.data.get("action", "RESOLVE")
        remarks = request.data.get("remarks", "")
        try:
            fb = feedback_service.resolve_or_close_feedback(
                pk, act, _actor(request), remarks=remarks
            )
            return Response(s.FeedbackSerializer(fb).data)
        except DomainError as e:
            raise ConflictError(str(e)) from e


class TimetableListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.TimetableEntrySerializer

    @extend_schema(responses={200: s.TimetableEntrySerializer(many=True)})
    def get(self, request):
        HasPermission("dept.timetable.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        p = request.query_params.get("program")
        year_param = request.query_params.get("year", "")
        sem_param = request.query_params.get("semester", "")
        y = int(year_param) if year_param.isdigit() else None
        sem = int(sem_param) if sem_param.isdigit() else None
        qs = list_timetables(dept, program=p, academic_year=y, semester=sem)
        return Response(s.TimetableEntrySerializer(qs, many=True).data)

    @extend_schema(request=s.TimetableEntrySerializer, responses={201: s.TimetableEntrySerializer})
    def post(self, request):
        if not HasPermission("dept.timetable.manage")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        try:
            start_t = datetime.time.fromisoformat(d.get("start_time"))
            end_t = datetime.time.fromisoformat(d.get("end_time"))
            entry = timetable_service.save_timetable_entry(
                department_code=dept,
                program=d.get("program", ""),
                academic_year=int(d.get("academic_year", 2026)),
                semester=int(d.get("semester", 1)),
                day_of_week=int(d.get("day_of_week", 0)),
                start_time=start_t,
                end_time=end_t,
                course_code=d.get("course_code", ""),
                course_name=d.get("course_name", ""),
                instructor_id=d.get("instructor_id", ""),
                room_or_lab=d.get("room_or_lab", ""),
            )
            return Response(s.TimetableEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
        except DomainConflictError as e:
            raise ConflictError(str(e)) from e
        except DomainError as e:
            raise BadRequestError(str(e)) from e


class TimetableDetailView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.timetable.manage")]
    serializer_class = s.TimetableEntrySerializer

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        timetable_service.delete_timetable_entry(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LabResourceListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.LabResourceSerializer

    @extend_schema(responses={200: s.LabResourceSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.lab_resource.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        qs = list_lab_resources(dept)
        return Response(s.LabResourceSerializer(qs, many=True).data)

    @extend_schema(request=s.LabResourceSerializer, responses={201: s.LabResourceSerializer})
    def post(self, request):
        if not HasPermission("dept.lab_resource.manage")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        lab = lab_service.save_lab_resource(
            department_code=dept,
            lab_name=d.get("lab_name", ""),
            location=d.get("location", ""),
            description=d.get("description", ""),
            equipment_details=d.get("equipment_details", []),
            in_charge_id=d.get("in_charge_id", ""),
        )
        return Response(s.LabResourceSerializer(lab).data, status=status.HTTP_201_CREATED)


class LabResourceDetailView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        MODULE,
        HasPermission("dept.lab_resource.manage"),
    ]
    serializer_class = s.LabResourceSerializer

    @extend_schema(request=s.LabResourceSerializer, responses={200: s.LabResourceSerializer})
    def patch(self, request, pk):
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        lab = lab_service.save_lab_resource(
            department_code=dept,
            lab_name=d.get("lab_name", ""),
            location=d.get("location", ""),
            description=d.get("description", ""),
            equipment_details=d.get("equipment_details"),
            in_charge_id=d.get("in_charge_id", ""),
            lab_id=pk,
        )
        return Response(s.LabResourceSerializer(lab).data)


class ProfileListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.UserProfileExtensionSerializer

    @extend_schema(responses={200: s.UserProfileExtensionSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.profile.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        t = request.query_params.get("type")
        qs = list_profiles(dept, profile_type=t)
        masked = [mask_profile_for_viewer(p, _actor(request)) for p in qs]
        return Response(masked)

    @extend_schema(
        request=s.UserProfileExtensionSerializer,
        responses={201: s.UserProfileExtensionSerializer},
    )
    def post(self, request):
        if not HasPermission("dept.profile.manage")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        prof = profile_service.save_user_profile_extension(
            department_code=dept,
            user_id=d.get("user_id", ""),
            profile_type=d.get("profile_type", "STUDENT"),
            office_room=d.get("office_room", ""),
            research_interests=d.get("research_interests", ""),
            contact_phone=d.get("contact_phone", ""),
            emergency_contact=d.get("emergency_contact", ""),
            courses_taught=d.get("courses_taught", []),
            batch_or_roll=d.get("batch_or_roll", ""),
            graduation_year=d.get("graduation_year"),
        )
        data = mask_profile_for_viewer(prof, _actor(request))
        return Response(data, status=status.HTTP_201_CREATED)


class DepartmentDetailView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.DepartmentSerializer

    @extend_schema(responses={200: s.DepartmentSerializer})
    def get(self, request):
        HasPermission("dept.detail.view")().has_permission(request, self)
        dept_code = resolve_department_code(_actor(request), request)
        info = get_department_with_headship(dept_code)
        if not info:
            department_service.update_general_department_info(dept_code)
            info = get_department_with_headship(dept_code)
        return Response(info)

    @extend_schema(request=s.DepartmentSerializer, responses={200: s.DepartmentSerializer})
    def patch(self, request):
        if not HasPermission("dept.detail.update")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept_code = resolve_department_code(_actor(request), request)
        desc = request.data.get("description")
        dept = department_service.update_general_department_info(dept_code, description=desc)
        return Response(get_department_with_headship(dept.code))


class OfficialChangeProposeView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.detail.update")]
    serializer_class = s.OfficialDetailChangeRequestSerializer

    @extend_schema(
        request=s.OfficialDetailChangeRequestSerializer,
        responses={201: s.OfficialDetailChangeRequestSerializer},
    )
    def post(self, request):
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        try:
            cr = department_service.propose_official_change(
                department_code=dept,
                proposer_principal=_actor(request),
                field_name=d.get("field_name", ""),
                new_value=d.get("new_value", ""),
                justification=d.get("justification", ""),
            )
            data = s.OfficialDetailChangeRequestSerializer(cr).data
            return Response(data, status=status.HTTP_201_CREATED)
        except DomainError as e:
            raise BadRequestError(str(e)) from e


class OfficialChangePendingListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.detail.approve")]
    serializer_class = s.OfficialDetailChangeRequestSerializer

    @extend_schema(responses={200: s.OfficialDetailChangeRequestSerializer(many=True)})
    def get(self, request):
        dept = resolve_department_code(_actor(request), request)
        qs = list_pending_official_changes(dept)
        return Response(s.OfficialDetailChangeRequestSerializer(qs, many=True).data)


class OfficialChangeDecisionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE, HasPermission("dept.detail.approve")]
    serializer_class = s.OfficialDetailChangeRequestSerializer

    @extend_schema(
        request=inline_serializer(
            name="OfficialChangeDecisionRequest",
            fields={
                "decision": drf_s.CharField(),
                "reason": drf_s.CharField(required=False, default=""),
            },
        ),
        responses={200: s.OfficialDetailChangeRequestSerializer},
    )
    def post(self, request, pk):
        dec = request.data.get("decision", "")
        reason = request.data.get("reason", "")
        try:
            cr = department_service.decide_official_change(pk, dec, _actor(request), reason=reason)
            return Response(s.OfficialDetailChangeRequestSerializer(cr).data)
        except DomainError as e:
            raise ConflictError(str(e)) from e


class RoleAssignmentListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, MODULE]
    serializer_class = s.DepartmentRoleAssignmentSerializer

    @extend_schema(responses={200: s.DepartmentRoleAssignmentSerializer(many=True)})
    def get(self, request):
        HasPermission("dept.role_assignment.view")().has_permission(request, self)
        dept = resolve_department_code(_actor(request), request)
        act = request.query_params.get("active_only", "").lower() in {"1", "true"}
        qs = list_role_assignments(dept, active_only=act)
        return Response(s.DepartmentRoleAssignmentSerializer(qs, many=True).data)

    @extend_schema(
        request=s.DepartmentRoleAssignmentSerializer,
        responses={201: s.DepartmentRoleAssignmentSerializer},
    )
    def post(self, request):
        if not HasPermission("dept.role_assignment.manage")().has_permission(request, self):
            raise PermissionDeniedError("Permission denied.")
        dept = resolve_department_code(_actor(request), request)
        d = request.data
        try:
            start_d = datetime.datetime.fromisoformat(d.get("start_date"))
            end_d = datetime.datetime.fromisoformat(d.get("end_date"))
            ra = role_service.assign_department_role(
                department_code=dept,
                role_name=d.get("role_name", "HOD"),
                user_id=d.get("user_id", ""),
                start_date=start_d,
                end_date=end_d,
                assigned_by_principal=_actor(request),
            )
            data = s.DepartmentRoleAssignmentSerializer(ra).data
            return Response(data, status=status.HTTP_201_CREATED)
        except DomainError as e:
            raise BadRequestError(str(e)) from e


class RoleAssignmentRevokeView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        MODULE,
        HasPermission("dept.role_assignment.manage"),
    ]
    serializer_class = s.DepartmentRoleAssignmentSerializer

    @extend_schema(responses={200: s.DepartmentRoleAssignmentSerializer})
    def post(self, request, pk):
        ra = role_service.revoke_department_role(pk, _actor(request))
        return Response(s.DepartmentRoleAssignmentSerializer(ra).data)
