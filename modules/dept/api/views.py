import logging
from datetime import time

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.dept.models import (
    Announcement,
    Department,
    DepartmentChange,
    InventoryItem,
    LabResource,
    Notification,
    StockRequest,
    TimetableSlot,
    UserProfile,
)
from modules.dept.selectors.scoping import department_scope
from modules.dept.services import operations as svc
from modules.directory.contracts import get_users, users_in_department

MODULE = HasModuleGrant("dept")
logger = logging.getLogger(__name__)


class DeptAutoSchema(AutoSchema):
    def get_operation_id(self):
        # APIView maps collection, detail, and action routes to generic HTTP methods.
        # Include the normalized URL path so every operation has a stable unique ID.
        path = (
            self.path.strip("/")
            .replace("{", "")
            .replace("}", "")
            .replace("-", "_")
            .replace("/", "_")
        )
        action = self.method_mapping[self.method.lower()]
        return f"{path}_{action}"

class DeptView(APIView):
    schema = DeptAutoSchema()
    throttle_scope = "dept_write"

    def get_throttles(self):
        # Reads are frequent in the shell; a write-only quota must not throttle
        # the page's independent list and inbox queries.
        self.throttle_scope = (
            "dept_read" if self.request.method in {"GET", "HEAD", "OPTIONS"} else "dept_write"
        )
        return super().get_throttles()

    def permission_classes_for(self):
        # Schema generation instantiates APIViews without URL kwargs.
        resource, action = self.kwargs.get("resource", ""), self.kwargs.get("action", "")
        method = self.request.method
        if resource == "stock-requests" and action in {"approve", "reject"}:
            code = "dept.stock_request.approve"
        elif resource == "stock-requests" and action in {"issue", "cancel"}:
            code = "dept.stock_request.update"
        elif resource == "feedback" and action:
            code = "dept.feedback.review"
        elif resource == "details" and action in {"approve", "reject"}:
            code = "dept.department.approve"
        else:
            codes = {
                "announcements": {
                    "GET": "dept.announcement.view",
                    "POST": "dept.announcement.create",
                    "PUT": "dept.announcement.update",
                    "PATCH": "dept.announcement.update",
                    "DELETE": "dept.announcement.update",
                },
                "inventory": {
                    "GET": "dept.stock_item.view",
                    "POST": "dept.stock_item.create",
                    "PUT": "dept.stock_item.update",
                    "PATCH": "dept.stock_item.update",
                    "DELETE": "dept.stock_item.update",
                },
                "stock-requests": {
                    "GET": "dept.stock_request.view",
                    "POST": "dept.stock_request.create",
                    "PUT": "dept.stock_request.update",
                    "PATCH": "dept.stock_request.update",
                    "DELETE": "dept.stock_request.update",
                },
                "feedback": {
                    "GET": "dept.feedback.view",
                    "POST": "dept.feedback.create",
                    "PUT": "dept.feedback.review",
                    "PATCH": "dept.feedback.review",
                    "DELETE": "dept.feedback.review",
                },
                "profiles": {
                    "GET": "dept.profile.view",
                    "POST": "dept.profile.update",
                    "PUT": "dept.profile.update",
                    "PATCH": "dept.profile.update",
                },
                "timetable": {
                    "GET": "dept.timetable.view",
                    "POST": "dept.timetable.create",
                    "PUT": "dept.timetable.update",
                    "PATCH": "dept.timetable.update",
                    "DELETE": "dept.timetable.update",
                },
                "resources": {
                    "GET": "dept.resource.view",
                    "POST": "dept.resource.create",
                    "PUT": "dept.resource.update",
                    "PATCH": "dept.resource.update",
                    "DELETE": "dept.resource.update",
                },
                "details": {
                    "GET": "dept.department.view",
                    "POST": "dept.department.update",
                    "PUT": "dept.department.update",
                    "PATCH": "dept.department.update",
                },
                "notifications": {
                    "GET": "dept.notification.view",
                    "POST": "dept.notification.update",
                    "PUT": "dept.notification.update",
                    "PATCH": "dept.notification.update",
                },
                "academic-info": {"GET": "dept.department.view"},
            }
            code = codes.get(resource, {}).get(method, "dept.department.view")
        return [MODULE(), HasPermission(code)()]

    def get_permissions(self):
        return self.permission_classes_for()

    def department(self, request):
        if self.kwargs["resource"] == "notifications":
            return None
        try:
            return department_scope(
                request.principal,
                request.query_params.get("department_code") or request.data.get("department_code"),
            )
        except KeyError as exc:
            raise ValidationError({"department_code": "Select a department."}) from exc

    def handle_exception(self, exc):
        if isinstance(exc, IamUnavailable):
            exc = APIException("The identity service is unavailable; retry this request.")
            exc.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        if isinstance(exc, ValueError):
            exc = ValidationError({"detail": str(exc)})
        return super().handle_exception(exc)

    @extend_schema(
        parameters=[OpenApiParameter("department_code", str, required=False)],
        responses=OpenApiTypes.OBJECT,
        examples=[OpenApiExample("Scoped list", value={"results": []})],
    )
    def get(self, request, resource, pk=None, action=None):
        dept = self.department(request)
        if resource == "announcements":
            qs = Announcement.objects.filter(
                department=dept, published=True, hidden=False, deleted_at__isnull=True
            )
            if request.principal.active_role not in {"HOD", "Dept_Admin"}:
                qs = qs.filter(target_roles__contains=[request.principal.kind])
                identity = get_users([request.principal.user_id]).get(request.principal.user_id)
                if identity:
                    qs = qs.filter(Q(programme="") | Q(programme=identity.programme))
                    qs = qs.filter(
                        Q(academic_year="") | Q(academic_year=str(identity.batch_year or ""))
                    )
            return Response([row(a) for a in qs.order_by("-created_at")[:200]])
        if resource == "inventory":
            return Response(
                [
                    row(x)
                    for x in InventoryItem.objects.filter(department=dept, active=True).order_by(
                        "name"
                    )
                ]
            )
        if resource == "stock-requests":
            qs = StockRequest.objects.filter(department=dept)
            if request.principal.active_role not in {"HOD", "Dept_Admin"}:
                qs = qs.filter(requester_user_id=request.principal.user_id)
            return Response([row(x) for x in qs.order_by("-created_at")[:200]])
        if resource == "feedback":
            return Response(
                [
                    row(x)
                    for x in svc.visible_feedback(request.principal, dept).order_by("-created_at")[
                        :200
                    ]
                ]
            )
        if resource == "profiles":
            actor = request.principal
            if actor.active_role in {"Dept_Admin", "HOD"}:
                kinds = ("student", "faculty", "staff", "alumni")
            elif actor.kind == "student":
                kinds = ("student", "faculty", "alumni")
            elif actor.kind == "faculty":
                kinds = ("faculty", "alumni")
            else:
                kinds = ()
            # IAM profiles may store the canonical code (CSE) while DEPT stores
            # the human-readable name. Match both representations for this scope.
            ids = users_in_department(department=(dept.code, dept.name), kinds=kinds)[:200]
            identities = get_users(ids)
            profiles = {
                p.user_id: p for p in UserProfile.objects.filter(department=dept, user_id__in=ids)
            }
            results = []
            for uid in ids:
                profile = identities.get(uid)
                if profile is None or (
                    actor.active_role not in {"Dept_Admin", "HOD"}
                    and actor.kind == "faculty"
                    and uid != actor.user_id
                    and profile.kind != "alumni"
                ):
                    continue
                extra = profiles.get(uid)
                results.append(
                    {
                        "user_id": uid,
                        "display_name": profile.display_name,
                        "kind": profile.kind,
                        "programme": profile.programme,
                        "discipline": profile.discipline,
                        "batch_year": profile.batch_year,
                        "details": extra.details if extra else {},
                    }
                )
            return Response(results)
        if resource == "timetable":
            return Response(
                [
                    row(x)
                    for x in TimetableSlot.objects.filter(department=dept).order_by(
                        "weekday", "starts_at"
                    )[:500]
                ]
            )
        if resource == "resources":
            return Response(
                [
                    row(x)
                    for x in LabResource.objects.filter(department=dept, active=True).order_by(
                        "name"
                    )[:200]
                ]
            )
        if resource == "details":
            result = row(dept)
            try:
                holders = get_client().get_department_appointments(dept.code)
            except IamUnavailable:
                logger.warning(
                    "dept.hod.lookup_unavailable",
                    extra={"department_code": dept.code},
                )
                holders = []
            result["head_user_id"] = next(
                (holder["user_id"] for holder in holders if holder["role"] == "HOD"), None
            )
            return Response(result)
        if resource == "academic-info":
            identity = get_users([request.principal.user_id]).get(request.principal.user_id)
            return Response(
                {
                    "programme": identity.programme if identity else "",
                    "discipline": identity.discipline if identity else "",
                    "batch_year": identity.batch_year if identity else None,
                    "department": dept.name,
                }
            )
        if resource == "notifications":
            return Response(
                [
                    row(n)
                    for n in Notification.objects.filter(
                        recipient_user_id=request.principal.user_id, read_at__isnull=True
                    ).order_by("-created_at")[:100]
                ]
            )
        raise ValidationError({"resource": "Unknown DEPT resource."})

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
        examples=[
            OpenApiExample(
                "Request body",
                value={"department_code": "CSE", "title": "Lab closure notice"},
                request_only=True,
            )
        ],
    )
    @transaction.atomic
    def post(self, request, resource, pk=None, action=None):
        dept = self.department(request)
        d = request.data
        actor = request.principal
        if resource == "announcements":
            item = svc.create_announcement(actor=actor, department=dept, data=d)
        elif resource == "inventory":
            item = svc.stock_insert(
                actor=actor,
                department=dept,
                item_id=d.get("item_id"),
                name=d.get("name", ""),
                description=d.get("description", ""),
                quantity=integer(d, "quantity"),
            )
        elif resource == "stock-requests" and not pk:
            item = svc.request_stock(
                actor=actor,
                department=dept,
                item_id=integer(d, "item_id"),
                quantity=integer(d, "quantity"),
                purpose=d.get("purpose", ""),
            )
        elif resource == "stock-requests" and action in {"approve", "reject", "issue"}:
            item = (
                svc.decide_stock(
                    actor=actor, request_id=pk, department=dept, approve=action == "approve"
                )
                if action in {"approve", "reject"}
                else svc.issue_stock(actor=actor, request_id=pk, department=dept)
            )
        elif resource == "feedback" and not pk:
            item = svc.submit_feedback(
                actor=actor, department=dept, title=d.get("title", ""), body=d.get("body", "")
            )
        elif resource == "feedback" and pk and action in {"review", "resolve", "close"}:
            item = svc.review_feedback(
                actor=actor,
                department=dept,
                feedback_id=pk,
                action=action,
                category=d.get("category", ""),
                resolution=d.get("resolution", ""),
            )
        elif resource == "profiles":
            if actor.active_role != "Dept_Admin":
                from core.api.exceptions import PermissionDeniedError

                raise PermissionDeniedError("Only Dept_Admin can maintain department profiles.")
            target_id = integer(d, "user_id")
            user = get_users([target_id]).get(target_id)
            if user is None or user.department.casefold() != dept.name.casefold():
                from core.api.exceptions import NotFoundError

                raise NotFoundError("Profile was not found.")
            details = d.get("details", {})
            allowed = {"office_location", "professional_bio", "expertise", "interests"}
            if (
                not isinstance(details, dict)
                or not set(details) <= allowed
                or any(not isinstance(v, str) or len(v) > 1000 for v in details.values())
            ):
                raise ValidationError(
                    {"details": "Use only the supported non-sensitive profile fields."}
                )
            item, _ = UserProfile.objects.update_or_create(
                department=dept,
                user_id=target_id,
                defaults={
                    "kind": user.kind,
                    "programme": user.programme,
                    "discipline": user.discipline,
                    "batch_year": user.batch_year,
                    "details": details,
                },
            )
        elif resource == "timetable":
            start, end = parse_time(d.get("starts_at")), parse_time(d.get("ends_at"))
            if end <= start:
                raise ValidationError({"ends_at": "Must be later than starts_at."})
            cohort, room, weekday = (
                d.get("cohort", "").strip(),
                d.get("resource", "").strip(),
                integer(d, "weekday"),
            )
            if not cohort or not room:
                raise ValidationError({"detail": "Cohort and resource are required."})
            with transaction.atomic():
                Department.objects.select_for_update().get(pk=dept.pk)
                conflict = (
                    TimetableSlot.objects.filter(
                        department=dept, weekday=weekday, starts_at__lt=end, ends_at__gt=start
                    )
                    .filter(Q(cohort=cohort) | Q(resource=room))
                    .exists()
                )
                if conflict:
                    from core.api.exceptions import ConflictError

                    raise ConflictError(
                        "This slot overlaps an existing cohort or resource booking.",
                        code="timetable_overlap",
                    )
                item = TimetableSlot.objects.create(
                    department=dept,
                    title=d.get("title", "").strip(),
                    cohort=cohort,
                    resource=room,
                    weekday=weekday,
                    starts_at=start,
                    ends_at=end,
                    instructor_user_id=d.get("instructor_user_id"),
                )
        elif resource == "resources":
            item = LabResource.objects.create(
                department=dept,
                name=d.get("name", "").strip(),
                location=d.get("location", "").strip(),
                details=d.get("details", {}),
            )
        elif resource == "details" and pk and action in {"approve", "reject"}:
            item = svc.decide_department_change(
                actor=actor,
                department=dept,
                change_id=pk,
                approve=action == "approve",
                note=d.get("note", ""),
            )
        elif resource == "details" and not pk:
            proposed = {k: v for k, v in d.items() if k != "department_code"}
            official_fields = {"name", "core_policies"}
            general_fields = {"description", "contact", "office_hours", "website"}
            if not set(proposed) <= official_fields | general_fields:
                raise ValidationError({"detail": "A department detail field is not supported."})
            general = {k: v for k, v in proposed.items() if k in general_fields}
            if general:
                dept.general_info = {**dept.general_info, **general}
                dept.save(update_fields=["general_info", "updated_at"])
            if set(proposed) & official_fields:
                item = DepartmentChange.objects.create(
                    department=dept,
                    proposed_by_user_id=actor.user_id,
                    proposed={k: proposed[k] for k in set(proposed) & official_fields},
                )
            else:
                item = dept
        elif resource == "notifications" and pk and action == "read":
            item = Notification.objects.filter(pk=pk, recipient_user_id=actor.user_id).first()
            if item is None:
                from core.api.exceptions import NotFoundError

                raise NotFoundError("Notification was not found.")
            item.read_at = timezone.now()
            item.save(update_fields=["read_at", "updated_at"])
        else:
            raise ValidationError({"detail": "This operation is not supported."})
        return Response(row(item), status=status.HTTP_201_CREATED)

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
        examples=[
            OpenApiExample("Update body", value={"title": "Updated notice"}, request_only=True)
        ],
    )
    def patch(self, request, resource, pk=None, action=None):
        if resource == "announcements" and pk:
            item = Announcement.objects.filter(
                pk=pk, department=self.department(request), deleted_at__isnull=True
            ).first()
            if item is None:
                from core.api.exceptions import NotFoundError

                raise NotFoundError("Announcement was not found.")
            for field in ("title", "body", "programme", "academic_year", "target_roles", "hidden"):
                if field in request.data:
                    setattr(item, field, request.data[field])
            item.save()
            return Response(row(item))
        if resource == "inventory" and pk:
            item = InventoryItem.objects.filter(pk=pk, department=self.department(request)).first()
            if item is None:
                from core.api.exceptions import NotFoundError

                raise NotFoundError("Inventory item was not found.")
            for field in ("name", "description", "active"):
                if field in request.data:
                    setattr(item, field, request.data[field])
            item.save()
            return Response(row(item))
        if resource == "resources" and pk:
            item = LabResource.objects.filter(pk=pk, department=self.department(request)).first()
            if item is None:
                from core.api.exceptions import NotFoundError

                raise NotFoundError("Lab resource was not found.")
            for field in ("name", "location", "details", "active"):
                if field in request.data:
                    setattr(item, field, request.data[field])
            item.save()
            return Response(row(item))
        if resource == "timetable" and pk:
            item = TimetableSlot.objects.filter(pk=pk, department=self.department(request)).first()
            if item is None:
                from core.api.exceptions import NotFoundError

                raise NotFoundError("Timetable entry was not found.")
            for field in ("title", "cohort", "resource", "weekday", "instructor_user_id"):
                if field in request.data:
                    setattr(item, field, request.data[field])
            if "starts_at" in request.data:
                item.starts_at = parse_time(request.data["starts_at"])
            if "ends_at" in request.data:
                item.ends_at = parse_time(request.data["ends_at"])
            if item.ends_at <= item.starts_at:
                raise ValidationError({"ends_at": "Must be later than starts_at."})
            with transaction.atomic():
                Department.objects.select_for_update().get(pk=item.department_id)
                if (
                    TimetableSlot.objects.filter(
                        department=item.department,
                        weekday=item.weekday,
                        starts_at__lt=item.ends_at,
                        ends_at__gt=item.starts_at,
                    )
                    .filter(Q(cohort=item.cohort) | Q(resource=item.resource))
                    .exclude(pk=item.pk)
                    .exists()
                ):
                    from core.api.exceptions import ConflictError

                    raise ConflictError(
                        "This slot overlaps an existing cohort or resource booking.",
                        code="timetable_overlap",
                    )
                item.save()
            return Response(row(item))
        if resource == "details" and action in {"approve", "reject"} and pk:
            return Response(
                row(
                    svc.decide_department_change(
                        actor=request.principal,
                        department=self.department(request),
                        change_id=pk,
                        approve=action == "approve",
                        note=request.data.get("note", ""),
                    )
                )
            )
        return self.post(request, resource, pk, action)

    @extend_schema(responses={204: OpenApiTypes.NONE})
    def delete(self, request, resource, pk=None, action=None):
        if resource != "announcements" or pk is None:
            raise ValidationError({"detail": "This operation is not supported."})
        item = Announcement.objects.filter(
            pk=pk, department=self.department(request), deleted_at__isnull=True
        ).first()
        if item is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("Announcement was not found.")
        item.deleted_at = timezone.now()
        item.save(update_fields=["deleted_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


def integer(data, key):
    try:
        return int(data.get(key))
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "Enter a whole number."}) from exc


def parse_time(value):
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"time": "Use 24-hour HH:MM time."}) from exc


def row(obj):
    if hasattr(obj, "_meta"):
        return {field.name: value(getattr(obj, field.name)) for field in obj._meta.fields}
    return obj


def value(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "pk"):
        return v.pk
    return v
