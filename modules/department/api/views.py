"""HTTP endpoints for the Department module's basic workflows."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api import serializers as s
from modules.department.models import (
    Announcement,
    DepartmentChange,
    DepartmentDetails,
    Feedback,
    InventoryItem,
    ResourceProfile,
    StockMovement,
    StockRequest,
    TimetableEntry,
)
from modules.department.services import department as service

MODULE = HasModuleGrant("department")


class DepartmentAPIView(APIView):
    """Apply both module and feature grants at the API boundary."""

    method_permissions = {}

    def get_permissions(self):
        permission = self.method_permissions.get(self.request.method)
        if permission is None:
            return [MODULE()]
        codes = permission if isinstance(permission, tuple) else (permission,)
        return [MODULE(), HasPermission(*codes)()]

    @staticmethod
    def department(actor):
        return service.department_for(actor)


class AnnouncementListView(DepartmentAPIView):
    method_permissions = {
        "GET": "department.announcement.view",
        "POST": "department.announcement.create",
    }

    def get(self, request):
        actor = request.principal
        person = service.directory_person(actor)
        role = (actor.active_role or "").strip().lower().replace(" ", "_")
        if role.startswith("department_"):
            role = role.removeprefix("department_")
        rows = service.relevant_announcements(
            department_code=self.department(actor), role=role,
            programme=person.programme if person else "",
            academic_year=str(person.batch_year or "") if person else "",
            manage_all_targets=actor.has_permission("department.announcement.manage"),
        )
        return Response({"results": s.AnnouncementSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.AnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        row = Announcement.objects.create(
            department_code=self.department(actor),
            created_by_user_id=actor.user_id,
            **payload.validated_data,
        )
        return Response(s.AnnouncementSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class AnnouncementActionView(DepartmentAPIView):
    method_permissions = {"POST": "department.announcement.manage"}

    def post(self, request, pk, action):
        row = Announcement.objects.filter(
            pk=pk, department_code=self.department(request.principal), status="active",
        ).first()
        if row is None:
            return Response({"detail": "Active announcement not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if action == "edit":
            payload = s.AnnouncementWriteSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            for key, value in payload.validated_data.items():
                setattr(row, key, value)
            row.save()
        elif action in ("hide", "delete"):
            row.status = "hidden" if action == "hide" else "deleted"
            row.save(update_fields=["status", "updated_at"])
        else:
            return Response({"detail": "Unknown announcement action."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(s.AnnouncementSerializer(row).data)


class InventoryView(DepartmentAPIView):
    method_permissions = {
        "GET": "department.inventory.view",
        "POST": "department.inventory.manage",
    }

    def get(self, request):
        actor = request.principal
        department_code = self.department(actor)
        items = InventoryItem.objects.filter(department_code=department_code)
        movements = StockMovement.objects.filter(
            department_code=department_code).select_related("item", "request")
        if not actor.has_permission("department.inventory.manage"):
            movements = movements.filter(
                movement="issue", request__faculty_user_id=actor.user_id)
        return Response({
            "items": s.InventoryItemSerializer(items, many=True).data,
            "movements": s.StockMovementSerializer(movements, many=True).data,
        })

    def post(self, request):
        payload = s.InventoryInsertSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        row = service.insert_stock(
            department_code=self.department(actor), actor_user_id=actor.user_id,
            **payload.validated_data,
        )
        return Response(s.InventoryItemSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class StockRequestView(DepartmentAPIView):
    method_permissions = {
        "GET": ("department.stock_request.review", "department.inventory.view"),
        "POST": "department.stock_request.create",
    }

    def get(self, request):
        actor = request.principal
        rows = StockRequest.objects.filter(
            department_code=self.department(actor)).select_related("item")
        if not actor.has_permission("department.stock_request.review"):
            rows = rows.filter(faculty_user_id=actor.user_id)
        return Response({"results": s.StockRequestSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.StockRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        row = service.request_stock(
            department_code=self.department(actor), actor_user_id=actor.user_id,
            **payload.validated_data,
        )
        return Response(s.StockRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class StockRequestActionView(DepartmentAPIView):
    def get_permissions(self):
        if self.request.method != "POST":
            return [MODULE()]
        permission = ("department.stock_request.issue" if self.kwargs.get("action") == "issue"
                     else "department.stock_request.review")
        return [MODULE(), HasPermission(permission)()]

    def post(self, request, pk, action):
        actor = request.principal
        department_code = self.department(actor)
        if action in ("approve", "reject"):
            if (actor.active_role or "").strip().lower() != "hod":
                return Response({"detail": "Only the HOD may decide a stock request."},
                                status=status.HTTP_403_FORBIDDEN)
            payload = s.DecisionSerializer(data={
                "decision": action, "note": request.data.get("note", "")})
            payload.is_valid(raise_exception=True)
            row = service.decide_stock_request(
                department_code=department_code, actor_user_id=actor.user_id,
                request_id=pk, **payload.validated_data,
            )
        elif action == "issue":
            if (actor.active_role or "").strip().lower() != "dept_admin":
                return Response({"detail": "Only Dept_Admin may issue stock."},
                                status=status.HTTP_403_FORBIDDEN)
            row = service.issue_stock_request(
                department_code=department_code, actor_user_id=actor.user_id,
                request_id=pk,
            )
        else:
            return Response({"detail": "Unknown stock request action."},
                            status=status.HTTP_400_BAD_REQUEST)
        row = StockRequest.objects.select_related("item").get(pk=row.pk)
        return Response(s.StockRequestSerializer(row).data)


class FeedbackView(DepartmentAPIView):
    method_permissions = {
        "GET": "department.feedback.view",
        "POST": "department.feedback.create",
    }

    def get(self, request):
        actor = request.principal
        rows = Feedback.objects.filter(department_code=self.department(actor))
        if actor.has_permission("department.feedback.review"):
            if (actor.active_role or "").strip().lower() == "hod":
                rows = rows.exclude(initial_reviewed_at__isnull=True)
        else:
            rows = rows.filter(submitter_user_id=actor.user_id)
        return Response({"results": s.FeedbackSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.FeedbackWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        row = Feedback.objects.create(
            department_code=self.department(actor),
            submitter_user_id=actor.user_id, **payload.validated_data)
        return Response(s.FeedbackSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class FeedbackReviewView(DepartmentAPIView):
    method_permissions = {"POST": "department.feedback.review"}

    def post(self, request, pk):
        actor = request.principal
        department_code = self.department(actor)
        role = (actor.active_role or "").strip().lower().replace(" ", "_")
        if role == "dept_admin" and "category" in request.data:
            payload = s.FeedbackReviewSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            row = service.review_feedback(
                department_code=department_code, actor_user_id=actor.user_id,
                feedback_id=pk, **payload.validated_data,
            )
        elif role in ("dept_admin", "hod"):
            payload = s.FeedbackDispositionSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            row = service.dispose_feedback(
                department_code=department_code, actor_user_id=actor.user_id,
                feedback_id=pk, **payload.validated_data,
            )
        else:
            return Response({"detail": "Only a feedback handler may review this item."},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(s.FeedbackSerializer(row).data)


class ResourceView(DepartmentAPIView):
    method_permissions = {
        "GET": "department.resource.view",
        "POST": "department.resource.manage",
    }

    def get(self, request):
        rows = ResourceProfile.objects.filter(
            department_code=self.department(request.principal))
        return Response({"results": s.ResourceSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.ResourceWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = ResourceProfile.objects.create(
            department_code=self.department(request.principal),
            **payload.validated_data)
        return Response(s.ResourceSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ResourceDetailView(DepartmentAPIView):
    method_permissions = {
        "PUT": "department.resource.manage",
        "PATCH": "department.resource.manage",
    }

    def put(self, request, pk):
        return self._update(request, pk)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial=False):
        row = ResourceProfile.objects.filter(
            pk=pk, department_code=self.department(request.principal)).first()
        if row is None:
            return Response({"detail": "Resource not found."},
                            status=status.HTTP_404_NOT_FOUND)
        payload = s.ResourceWriteSerializer(data=request.data, partial=partial)
        payload.is_valid(raise_exception=True)
        for key, value in payload.validated_data.items():
            setattr(row, key, value)
        row.save()
        return Response(s.ResourceSerializer(row).data)


class TimetableView(DepartmentAPIView):
    method_permissions = {
        "GET": ("department.timetable.view", "department.timetable.manage"),
        "POST": "department.timetable.manage",
    }

    def get(self, request):
        actor = request.principal
        rows = TimetableEntry.objects.filter(
            department_code=self.department(actor))
        if (actor.has_permission("department.timetable.view")
                and not actor.has_permission("department.timetable.manage")):
            person = service.directory_person(actor)
            if person and person.programme:
                rows = rows.filter(programme=person.programme)
            if person and person.batch_year:
                rows = rows.filter(academic_year=str(person.batch_year))
        return Response({"results": s.TimetableSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.TimetableWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        row = service.save_timetable_entry(
            department_code=self.department(actor), actor_user_id=actor.user_id,
            entry=payload.validated_data,
        )
        return Response(s.TimetableSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class TimetableDetailView(DepartmentAPIView):
    method_permissions = {"PUT": "department.timetable.manage"}

    def put(self, request, pk):
        payload = s.TimetableWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.save_timetable_entry(
            department_code=self.department(request.principal),
            actor_user_id=request.principal.user_id,
            entry=payload.validated_data, entry_id=pk,
        )
        return Response(s.TimetableSerializer(row).data)


class DepartmentDetailsView(DepartmentAPIView):
    method_permissions = {
        "GET": "department.details.view",
        "PATCH": "department.details.manage",
        "POST": "department.details.manage",
    }

    def get(self, request):
        actor = request.principal
        department_code = self.department(actor)
        row = DepartmentDetails.objects.filter(department_code=department_code).first()
        details = (s.DepartmentDetailsSerializer(row).data
                   if row else {"general": {}, "official": {}})
        changes = (DepartmentChange.objects.filter(
            department_code=department_code, status="pending_hod_approval")
            if (actor.has_permission("department.details.manage")
                or actor.has_permission("department.details.approve")) else [])
        details["changes"] = s.DepartmentChangeSerializer(changes, many=True).data
        return Response(details)

    def patch(self, request):
        payload = s.GeneralDetailsWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        department_code = self.department(request.principal)
        row, _ = DepartmentDetails.objects.get_or_create(
            department_code=department_code)
        row.general = {**row.general, **payload.validated_data["general"]}
        row.save(update_fields=["general", "updated_at"])
        return Response(s.DepartmentDetailsSerializer(row).data)

    def post(self, request):
        payload = s.OfficialChangeWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        row = DepartmentChange.objects.create(
            department_code=self.department(actor),
            proposed_by_user_id=actor.user_id, **payload.validated_data)
        return Response(s.DepartmentChangeSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class DepartmentChangeActionView(DepartmentAPIView):
    method_permissions = {"POST": "department.details.approve"}

    def post(self, request, pk, action):
        if action not in ("approve", "reject"):
            return Response({"detail": "Unknown department change action."},
                            status=status.HTTP_400_BAD_REQUEST)
        payload = s.DepartmentChangeDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.decide_department_change(
            department_code=self.department(request.principal),
            actor_user_id=request.principal.user_id,
            change_id=pk, decision=action,
            **payload.validated_data,
        )
        return Response(s.DepartmentChangeSerializer(row).data)
