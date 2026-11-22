"""HTTP layer: parse, scope, delegate, serialise. Two gates on every endpoint."""

from __future__ import annotations

import re

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api import serializers as s
from modules.department.models import Feedback, StockRequest
from modules.department.selectors import profiles as profile_selectors
from modules.department.selectors import scoping
from modules.department.selectors.actors import context_for
from modules.department.selectors.readiness import role_warnings
from modules.department.services import announcements as announcement_service
from modules.department.services import departments as department_service
from modules.department.services import feedback as feedback_service
from modules.department.services import inventory as inventory_service
from modules.department.services import resources as resource_service
from modules.department.services import roles as role_service

MODULE = HasModuleGrant("department")


class DenyAll(BasePermission):
    """A method with no permission named for it is refused, never left to the module gate alone."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return False


SAFE = frozenset({"GET", "HEAD", "OPTIONS"})
DEPT_CODE = re.compile(r"[A-Za-z]{1,12}")


def _ex(name: str, value: dict, *, request: bool = False) -> OpenApiExample:
    return OpenApiExample(name, value=value, request_only=request, response_only=not request)


def _status_filter(params, allowed) -> str | None:
    raw = params.get("status")
    if raw in (None, ""):
        return None
    if raw not in allowed:
        raise BadRequestError(
            f"status must be one of: {', '.join(allowed)}.", code="invalid_filter"
        )
    return raw


class DepartmentView(APIView):
    """Each HTTP method names its permission; writes are throttled, reads are not."""

    perms: dict[str, str] = {}
    throttle_scope = "department_write"

    def get_permissions(self):
        method = self.request.method
        code = self.perms.get("GET" if method in ("HEAD", "OPTIONS") else method)
        if code is None:
            return [MODULE(), DenyAll()]
        return [MODULE(), HasPermission(code)()]

    def get_throttles(self):
        return [] if self.request.method in SAFE else super().get_throttles()

    @property
    def ctx(self):
        if not hasattr(self, "_ctx"):
            self._ctx = context_for(getattr(self.request, "principal", None))
        return self._ctx

    def paginated(self, queryset, serializer_class, **context):
        paginator = CursorPagination()
        page = paginator.paginate_queryset(queryset.order_by("-id"), self.request, view=self)
        return paginator.get_paginated_response(
            serializer_class(page, many=True, context=context).data
        )


# -- departments and official changes --------------------------------------------
def _programmes() -> list[str]:
    try:
        return list(get_client().academic_filters().get("programmes", []))
    except IamUnavailable:
        return []


@extend_schema(
    responses=s.DeptDepartmentSerializer(many=True),
    examples=[
        _ex(
            "Department",
            {
                "id": 1,
                "code": "CSE",
                "name": "Computer Science and Engineering",
                "headship": {"user_id": 49, "display_name": "Head"},
            },
        )
    ],
)
class DepartmentListView(DepartmentView):
    perms = {"GET": "department.department.view"}

    def get(self, request):
        depts = list(scoping.departments_for(self.ctx))
        heads = profile_selectors.headships(depts)
        return Response(
            s.DeptDepartmentSerializer(depts, many=True, context={"headships": heads}).data
        )


class DepartmentDetailView(DepartmentView):
    perms = {"GET": "department.department.view", "PATCH": "department.department.update"}

    @staticmethod
    def _code(code):
        """R4-01: a code the column could never hold is a 404 before it reaches the database."""
        if not DEPT_CODE.fullmatch(code):
            raise NotFoundError("That department does not exist or is not yours.")
        return code

    def _dept(self, code):
        dept = scoping.departments_for(self.ctx).filter(code=self._code(code)).first()
        if dept is None:
            raise NotFoundError("That department does not exist or is not yours.")
        return dept

    def _render(self, dept):
        ctx = {"headships": profile_selectors.headships([dept]), "programmes": _programmes()}
        return Response(s.DeptDepartmentSerializer(dept, context=ctx).data)

    @extend_schema(
        responses=s.DeptDepartmentSerializer,
        examples=[
            _ex(
                "Details",
                {
                    "code": "CSE",
                    "name": "Computer Science and Engineering",
                    "programmes": ["B.Tech"],
                    "headship": None,
                },
            )
        ],
    )
    def get(self, request, code):
        return self._render(self._dept(code))

    @extend_schema(
        request=s.DeptGeneralUpdateSerializer,
        responses=s.DeptDepartmentSerializer,
        examples=[
            _ex("General update", {"contact_email": "cse@iiitdmj.ac.in"}, request=True),
            _ex("Updated", {"code": "CSE", "contact_email": "cse@iiitdmj.ac.in"}),
        ],
    )
    def patch(self, request, code):
        payload = s.DeptGeneralUpdateSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        return self._render(
            department_service.update_general(self.ctx, self._code(code), **payload.validated_data)
        )


class OfficialChangeListView(DepartmentView):
    perms = {"GET": "department.official_change.view", "POST": "department.official_change.create"}

    @extend_schema(
        responses=s.DeptOfficialChangeSerializer(many=True),
        examples=[_ex("Pending", {"id": 3, "field": "name", "status": "pending"})],
    )
    def get(self, request):
        qs = scoping.official_changes_for(self.ctx)
        wanted = _status_filter(request.query_params, ("pending", "approved", "rejected"))
        if wanted:
            qs = qs.filter(status=wanted)
        return self.paginated(qs, s.DeptOfficialChangeSerializer)

    @extend_schema(
        request=s.DeptOfficialChangeWriteSerializer,
        responses={201: s.DeptOfficialChangeSerializer},
        examples=[
            _ex("Propose", {"field": "name", "value": "CSE Department"}, request=True),
            _ex("Pending", {"id": 3, "field": "name", "status": "pending"}),
        ],
    )
    def post(self, request):
        payload = s.DeptOfficialChangeWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        change = department_service.propose(self.ctx, **payload.validated_data)
        return Response(s.DeptOfficialChangeSerializer(change).data, status=status.HTTP_201_CREATED)


class OfficialChangeDecideView(DepartmentView):
    perms = {"POST": "department.official_change.approve"}

    @extend_schema(
        request=s.DeptDecisionSerializer,
        responses=s.DeptOfficialChangeSerializer,
        examples=[
            _ex("Approve", {"approve": True}, request=True),
            _ex("Approved", {"id": 3, "status": "approved"}),
        ],
    )
    def post(self, request, pk):
        payload = s.DeptDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        change = department_service.decide(self.ctx, pk, **payload.validated_data)
        return Response(s.DeptOfficialChangeSerializer(change).data)


# -- announcements ---------------------------------------------------------------
ANN_EXAMPLE = {
    "id": 7,
    "title": "Lab closed Friday",
    "audience_role": "student",
    "status": "active",
}


class AnnouncementListView(DepartmentView):
    perms = {"GET": "department.announcement.view", "POST": "department.announcement.create"}

    @extend_schema(
        responses=s.DeptAnnouncementSerializer(many=True), examples=[_ex("Feed", ANN_EXAMPLE)]
    )
    def get(self, request):
        return self.paginated(scoping.announcements_for(self.ctx), s.DeptAnnouncementSerializer)

    @extend_schema(
        request=s.DeptAnnouncementWriteSerializer,
        responses={201: s.DeptAnnouncementSerializer},
        examples=[
            _ex(
                "Publish",
                {
                    "title": "Lab closed Friday",
                    "body": "Maintenance.",
                    "audience_role": "student",
                    "programme": "B.Tech",
                    "batch_year": 2024,
                },
                request=True,
            ),
            _ex("Published", ANN_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptAnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        ann = announcement_service.publish(self.ctx, **payload.validated_data)
        return Response(s.DeptAnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


class AnnouncementDetailView(DepartmentView):
    perms = {"PATCH": "department.announcement.update", "DELETE": "department.announcement.delete"}

    @extend_schema(
        request=s.DeptAnnouncementEditSerializer,
        responses=s.DeptAnnouncementSerializer,
        examples=[
            _ex("Edit", {"title": "Lab closed Saturday"}, request=True),
            _ex("Edited", ANN_EXAMPLE),
        ],
    )
    def patch(self, request, pk):
        payload = s.DeptAnnouncementEditSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        return Response(
            s.DeptAnnouncementSerializer(
                announcement_service.edit(self.ctx, pk, **payload.validated_data)
            ).data
        )

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk):
        announcement_service.delete(self.ctx, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnnouncementHideView(DepartmentView):
    perms = {"POST": "department.announcement.update"}

    @extend_schema(
        request=None,
        responses=s.DeptAnnouncementSerializer,
        examples=[_ex("Hidden", {**ANN_EXAMPLE, "status": "hidden"})],
    )
    def post(self, request, pk):
        return Response(s.DeptAnnouncementSerializer(announcement_service.hide(self.ctx, pk)).data)


# -- inventory and stock ---------------------------------------------------------
ITEM_EXAMPLE = {"id": 2, "name": "Arduino Uno", "unit": "board", "current_quantity": 18}
REQ_EXAMPLE = {
    "id": 11,
    "item": 2,
    "item_name": "Arduino Uno",
    "quantity": 4,
    "status": "pending_hod",
}


class InventoryItemListView(DepartmentView):
    perms = {"GET": "department.inventory_item.view", "POST": "department.inventory_item.create"}

    @extend_schema(
        responses=s.DeptInventoryItemSerializer(many=True), examples=[_ex("Items", ITEM_EXAMPLE)]
    )
    def get(self, request):
        return self.paginated(scoping.inventory_items_for(self.ctx), s.DeptInventoryItemSerializer)

    @extend_schema(
        request=s.DeptInventoryItemWriteSerializer,
        responses={201: s.DeptInventoryItemSerializer},
        examples=[
            _ex("Add", {"name": "Arduino Uno", "unit": "board", "quantity": 20}, request=True),
            _ex("Added", ITEM_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptInventoryItemWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = inventory_service.add_item(self.ctx, **payload.validated_data)
        return Response(s.DeptInventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InventoryReceiptView(DepartmentView):
    perms = {"POST": "department.inventory_item.create"}

    @extend_schema(
        request=s.DeptReceiptSerializer,
        responses={201: s.DeptInventoryItemSerializer},
        examples=[_ex("Receipt", {"quantity": 10}, request=True), _ex("Item", ITEM_EXAMPLE)],
    )
    def post(self, request, pk):
        payload = s.DeptReceiptSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = inventory_service.receive(self.ctx, pk, **payload.validated_data)
        return Response(s.DeptInventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class StockMovementListView(DepartmentView):
    perms = {"GET": "department.stock_movement.view"}

    @extend_schema(
        responses=s.DeptStockMovementSerializer(many=True),
        examples=[_ex("Ledger", {"id": 5, "item": 2, "kind": "issue", "quantity": 4})],
    )
    def get(self, request):
        return self.paginated(scoping.stock_movements_for(self.ctx), s.DeptStockMovementSerializer)


class StockRequestListView(DepartmentView):
    perms = {"GET": "department.stock_request.view", "POST": "department.stock_request.create"}

    @extend_schema(
        responses=s.DeptStockRequestSerializer(many=True), examples=[_ex("Requests", REQ_EXAMPLE)]
    )
    def get(self, request):
        qs = scoping.stock_requests_for(self.ctx)
        wanted = _status_filter(request.query_params, [c for c, _ in StockRequest.STATUS])
        if wanted:
            qs = qs.filter(status=wanted)
        return self.paginated(qs, s.DeptStockRequestSerializer)

    @extend_schema(
        request=s.DeptStockRequestWriteSerializer,
        responses={201: s.DeptStockRequestSerializer},
        examples=[
            _ex("Request", {"item": 2, "quantity": 4, "purpose": "IoT lab"}, request=True),
            _ex("Pending", REQ_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptStockRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        req = inventory_service.request_stock(
            self.ctx, item_id=data["item"], quantity=data["quantity"], purpose=data["purpose"]
        )
        return Response(s.DeptStockRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class StockRequestDecideView(DepartmentView):
    perms = {"POST": "department.stock_request.approve"}

    @extend_schema(
        request=s.DeptDecisionSerializer,
        responses=s.DeptStockRequestSerializer,
        examples=[
            _ex("Approve", {"approve": True}, request=True),
            _ex("Approved", {**REQ_EXAMPLE, "status": "approved"}),
        ],
    )
    def post(self, request, pk):
        payload = s.DeptDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return Response(
            s.DeptStockRequestSerializer(
                inventory_service.decide(self.ctx, pk, **payload.validated_data)
            ).data
        )


class StockRequestIssueView(DepartmentView):
    perms = {"POST": "department.stock_issue.create"}

    @extend_schema(
        request=None,
        responses=s.DeptStockRequestSerializer,
        examples=[_ex("Issued", {**REQ_EXAMPLE, "status": "issued"})],
    )
    def post(self, request, pk):
        return Response(s.DeptStockRequestSerializer(inventory_service.issue(self.ctx, pk)).data)


# -- feedback --------------------------------------------------------------------
FB_EXAMPLE = {"id": 4, "subject": "Projector broken", "status": "new", "category": "", "notes": []}


def _feedback_qs(ctx):
    return scoping.feedback_for(ctx).prefetch_related("notes")


class FeedbackListView(DepartmentView):
    perms = {"GET": "department.feedback.view", "POST": "department.feedback.create"}

    @extend_schema(
        responses=s.DeptFeedbackSerializer(many=True), examples=[_ex("Feedback", FB_EXAMPLE)]
    )
    def get(self, request):
        qs = _feedback_qs(self.ctx)
        wanted = _status_filter(request.query_params, [c for c, _ in Feedback.STATUS])
        if wanted:
            qs = qs.filter(status=wanted)
        return self.paginated(qs, s.DeptFeedbackSerializer)

    @extend_schema(
        request=s.DeptFeedbackWriteSerializer,
        responses={201: s.DeptFeedbackSerializer},
        examples=[
            _ex("Submit", {"subject": "Projector broken", "body": "Room L-104"}, request=True),
            _ex("Submitted", FB_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptFeedbackWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        fb = feedback_service.submit(self.ctx, **payload.validated_data)
        return Response(s.DeptFeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)


class FeedbackDetailView(DepartmentView):
    perms = {"GET": "department.feedback.view"}

    @extend_schema(responses=s.DeptFeedbackSerializer, examples=[_ex("Feedback", FB_EXAMPLE)])
    def get(self, request, pk):
        fb = _feedback_qs(self.ctx).filter(pk=pk).first()
        if fb is None:
            raise NotFoundError("That feedback does not exist or is not visible to you.")
        return Response(s.DeptFeedbackSerializer(fb).data)


class FeedbackReviewView(DepartmentView):
    perms = {"POST": "department.feedback.review"}

    @extend_schema(
        request=s.DeptFeedbackReviewSerializer,
        responses=s.DeptFeedbackSerializer,
        examples=[
            _ex("Review", {"category": "facilities"}, request=True),
            _ex("Reviewed", {**FB_EXAMPLE, "status": "under_review", "category": "facilities"}),
        ],
    )
    def post(self, request, pk):
        payload = s.DeptFeedbackReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        feedback_service.review(self.ctx, pk, **payload.validated_data)
        return Response(s.DeptFeedbackSerializer(_feedback_qs(self.ctx).get(pk=pk)).data)


class FeedbackDisposeView(DepartmentView):
    perms = {"POST": "department.feedback_resolution.create"}

    @extend_schema(
        request=s.DeptFeedbackDisposeSerializer,
        responses=s.DeptFeedbackSerializer,
        examples=[
            _ex("Resolve", {"outcome": "resolved", "note": "Replaced"}, request=True),
            _ex("Resolved", {**FB_EXAMPLE, "status": "resolved"}),
        ],
    )
    def post(self, request, pk):
        payload = s.DeptFeedbackDisposeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        feedback_service.dispose(self.ctx, pk, **payload.validated_data)
        return Response(s.DeptFeedbackSerializer(_feedback_qs(self.ctx).get(pk=pk)).data)


class FeedbackNoteView(DepartmentView):
    perms = {"POST": "department.feedback_resolution.create"}

    @extend_schema(
        request=s.DeptFeedbackNoteWriteSerializer,
        responses={201: s.DeptFeedbackNoteSerializer},
        examples=[
            _ex("Note", {"body": "Following up with IWD."}, request=True),
            _ex("Saved", {"id": 1, "body": "Following up with IWD."}),
        ],
    )
    def post(self, request, pk):
        payload = s.DeptFeedbackNoteWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        note = feedback_service.add_note(self.ctx, pk, **payload.validated_data)
        return Response(s.DeptFeedbackNoteSerializer(note).data, status=status.HTTP_201_CREATED)


# -- timetable, labs, profiles ---------------------------------------------------
SLOT_EXAMPLE = {
    "kind": "class",
    "programme": "B.Tech",
    "batch_year": 2024,
    "course_code": "CS2003",
    "day_of_week": 0,
    "starts_at": "09:00",
    "ends_at": "10:00",
    "room": "L-104",
}


class TimetableListView(DepartmentView):
    perms = {"GET": "department.timetable.view", "POST": "department.timetable.create"}

    @extend_schema(
        responses=s.DeptTimetableSlotSerializer(many=True), examples=[_ex("Slots", SLOT_EXAMPLE)]
    )
    def get(self, request):
        qs = scoping.timetable_for(self.ctx).order_by("day_of_week", "starts_at", "id")
        return Response(s.DeptTimetableSlotSerializer(qs, many=True).data)

    @extend_schema(
        request=s.DeptTimetableUploadSerializer,
        responses={201: s.DeptTimetableSlotSerializer(many=True)},
        examples=[
            _ex("Upload", {"slots": [SLOT_EXAMPLE]}, request=True),
            _ex("Saved", SLOT_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptTimetableUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        slots = resource_service.upload(self.ctx, payload.validated_data["slots"])
        return Response(
            s.DeptTimetableSlotSerializer(slots, many=True).data, status=status.HTTP_201_CREATED
        )


class TimetableDetailView(DepartmentView):
    perms = {"PATCH": "department.timetable.update", "DELETE": "department.timetable.update"}

    @extend_schema(
        request=s.DeptTimetableSlotEditSerializer,
        responses=s.DeptTimetableSlotSerializer,
        examples=[_ex("Move", {"room": "L-105"}, request=True), _ex("Moved", SLOT_EXAMPLE)],
    )
    def patch(self, request, pk):
        payload = s.DeptTimetableSlotEditSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        return Response(
            s.DeptTimetableSlotSerializer(
                resource_service.modify(self.ctx, pk, **payload.validated_data)
            ).data
        )

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk):
        resource_service.remove(self.ctx, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


LAB_EXAMPLE = {
    "id": 1,
    "name": "IoT Lab",
    "location": "Block C",
    "equipment": "Oscilloscopes x10",
    "capacity": 30,
    "status": "available",
}


class LabListView(DepartmentView):
    perms = {"GET": "department.lab_resource.view", "POST": "department.lab_resource.update"}

    @extend_schema(
        responses=s.DeptLabResourceSerializer(many=True), examples=[_ex("Labs", LAB_EXAMPLE)]
    )
    def get(self, request):
        return self.paginated(scoping.lab_resources_for(self.ctx), s.DeptLabResourceSerializer)

    @extend_schema(
        request=s.DeptLabResourceEditSerializer,
        responses={201: s.DeptLabResourceSerializer},
        examples=[
            _ex("Add", {"name": "IoT Lab", "capacity": 30}, request=True),
            _ex("Added", LAB_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptLabResourceEditSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        lab = resource_service.save_lab(self.ctx, **payload.validated_data)
        return Response(s.DeptLabResourceSerializer(lab).data, status=status.HTTP_201_CREATED)


class LabDetailView(DepartmentView):
    perms = {"PATCH": "department.lab_resource.update"}

    @extend_schema(
        request=s.DeptLabResourceEditSerializer,
        responses=s.DeptLabResourceSerializer,
        examples=[
            _ex("Update", {"status": "maintenance"}, request=True),
            _ex("Updated", LAB_EXAMPLE),
        ],
    )
    def patch(self, request, pk):
        payload = s.DeptLabResourceEditSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        return Response(
            s.DeptLabResourceSerializer(
                resource_service.save_lab(self.ctx, pk, **payload.validated_data)
            ).data
        )


PROFILE_EXAMPLE = {
    "tier": "basic",
    "id": 9,
    "kind": "faculty",
    "display_name": "A. Rao",
    "programme": "",
    "department": "CSE",
}


class ProfileListView(DepartmentView):
    perms = {"GET": "department.profile.view", "POST": "department.profile.update"}

    @extend_schema(
        responses=s.DeptProfileViewSerializer(many=True), examples=[_ex("People", PROFILE_EXAMPLE)]
    )
    def get(self, request):
        paginator = CursorPagination()
        page = paginator.paginate_queryset(
            scoping.profiles_for(self.ctx).order_by("-id"), request, view=self
        )
        return paginator.get_paginated_response(profile_selectors.profile_views(self.ctx, page))

    @extend_schema(
        request=s.DeptProfileWriteSerializer,
        responses={201: s.DeptProfileViewSerializer},
        examples=[
            _ex(
                "Add",
                {"kind": "alumni", "display_name": "B. Sen", "graduation_year": 2019},
                request=True,
            ),
            _ex("Added", {**PROFILE_EXAMPLE, "tier": "full"}),
        ],
    )
    def post(self, request):
        payload = s.DeptProfileWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = resource_service.create_profile(self.ctx, **payload.validated_data)
        return Response(
            profile_selectors.profile_views(self.ctx, [record])[0], status=status.HTTP_201_CREATED
        )


class ProfileDetailView(DepartmentView):
    perms = {"GET": "department.profile.view", "PATCH": "department.profile.update"}

    @extend_schema(
        responses=s.DeptProfileViewSerializer, examples=[_ex("Profile", PROFILE_EXAMPLE)]
    )
    def get(self, request, pk):
        record = scoping.profiles_for(self.ctx).filter(pk=pk).first()
        views = profile_selectors.profile_views(self.ctx, [record]) if record else []
        if not views:
            raise NotFoundError("That profile does not exist or is not visible to you.")
        return Response(views[0])

    @extend_schema(
        request=s.DeptProfileEditSerializer,
        responses=s.DeptProfileViewSerializer,
        examples=[
            _ex("Edit", {"office": "C-210"}, request=True),
            _ex("Edited", {**PROFILE_EXAMPLE, "tier": "full"}),
        ],
    )
    def patch(self, request, pk):
        payload = s.DeptProfileEditSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        record = resource_service.update_profile(self.ctx, pk, **payload.validated_data)
        return Response(profile_selectors.profile_views(self.ctx, [record])[0])


# -- role tenures ----------------------------------------------------------------
TENURE_EXAMPLE = {
    "id": 1,
    "department": "CSE",
    "role": "hod",
    "user_id": 49,
    "valid_from": "2026-12-01T00:00:00+05:30",
    "valid_to": "2029-11-30T00:00:00+05:30",
    "in_effect": False,
}


class RoleTenureListView(DepartmentView):
    perms = {"GET": "department.role_assignment.view", "POST": "department.role_assignment.assign"}

    @extend_schema(
        responses=s.DeptRoleTenureSerializer(many=True), examples=[_ex("Tenures", TENURE_EXAMPLE)]
    )
    def get(self, request):
        return self.paginated(
            scoping.tenures_for(self.ctx), s.DeptRoleTenureSerializer, now=timezone.now()
        )

    @extend_schema(
        request=s.DeptRoleTenureWriteSerializer,
        responses={201: s.DeptRoleTenureSerializer},
        examples=[
            _ex(
                "Assign",
                {
                    "department": "CSE",
                    "role": "hod",
                    "user_id": 49,
                    "valid_from": TENURE_EXAMPLE["valid_from"],
                    "valid_to": TENURE_EXAMPLE["valid_to"],
                },
                request=True,
            ),
            _ex("Recorded", TENURE_EXAMPLE),
        ],
    )
    def post(self, request):
        payload = s.DeptRoleTenureWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        tenure = role_service.assign(
            self.ctx,
            department_code=data["department"],
            role=data["role"],
            user_id=data["user_id"],
            valid_from=data["valid_from"],
            valid_to=data["valid_to"],
        )
        return Response(
            s.DeptRoleTenureSerializer(tenure, context={"now": timezone.now()}).data,
            status=status.HTTP_201_CREATED,
        )


class RoleTenureDetailView(DepartmentView):
    perms = {"PATCH": "department.role_assignment.assign"}

    @extend_schema(
        request=s.DeptRoleTenureEditSerializer,
        responses=s.DeptRoleTenureSerializer,
        examples=[
            _ex("Extend", {"valid_to": "2030-11-30T00:00:00+05:30"}, request=True),
            _ex("Changed", TENURE_EXAMPLE),
        ],
    )
    def patch(self, request, pk):
        payload = s.DeptRoleTenureEditSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenure = role_service.change(self.ctx, pk, valid_to=payload.validated_data["valid_to"])
        return Response(s.DeptRoleTenureSerializer(tenure, context={"now": timezone.now()}).data)


class RoleVacancyView(DepartmentView):
    """Q1 mitigation for BR-DEPT-022: vacant or ending roles in the departments you can see."""

    perms = {"GET": "department.role_assignment.view"}

    @extend_schema(
        responses=s.DeptRoleWarningSerializer(many=True),
        examples=[
            _ex(
                "Vacant",
                {
                    "department": "SM",
                    "role": "hod",
                    "problem": "vacant",
                    "message": "SM has no HOD in effect.",
                },
            )
        ],
    )
    def get(self, request):
        depts = list(scoping.departments_for(self.ctx))
        return Response(s.DeptRoleWarningSerializer(role_warnings(depts), many=True).data)


class ActingContextView(DepartmentView):
    """The acting role and department, so the client shows only that role's controls."""

    perms = {"GET": "department.department.view"}

    @extend_schema(
        responses=s.DeptActingSerializer,
        examples=[_ex("HOD", {"role": "hod", "department": "CSE"})],
    )
    def get(self, request):
        return Response(
            s.DeptActingSerializer({"role": self.ctx.role, "department": self.ctx.department}).data
        )
