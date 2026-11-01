from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import DomainError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.lms.api import forms
from modules.lms.api import serializers as s
from modules.lms.models import Assignment, Material
from modules.lms.selectors import queries as q
from modules.lms.services import courses as services


class LmsView(APIView):
    permission_classes = [HasModuleGrant("lms"), HasPermission("lms.course.view")]


class Courses(LmsView):
    @extend_schema(operation_id="lms_courses_list", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"results": services.open_courses(request.principal)})


class CourseDetail(LmsView):
    @extend_schema(operation_id="lms_workspace_retrieve", responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        workspace, context = services.workspace_context(request.principal, pk)
        services.release_due()
        role = context["role"]
        return Response(
            {
                "id": workspace.pk,
                "course": context,
                "syllabus": workspace.syllabus,
                "schedule": workspace.schedule,
                "materials": s.MaterialSerializer(q.materials(workspace, role), many=True).data,
                "assignments": s.AssignmentSerializer(
                    q.assignments(workspace, role), many=True
                ).data,
                "announcements": s.AnnouncementSerializer(
                    workspace.announcements.order_by("-created_at"), many=True
                ).data,
                "submissions": s.SubmissionSerializer(
                    q.submissions(workspace, role, request.principal.user_id),
                    many=True,
                    context={"reviewer": role in ("faculty", "ta")},
                ).data,
            }
        )


class WriteContent(LmsView):
    @extend_schema(
        operation_id="lms_content_create",
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, pk, kind, item_id=None):
        definitions = {
            "details": (None, forms.WorkspaceForm),
            "material": (Material, forms.MaterialForm),
            "assignment": (Assignment, forms.AssignmentForm),
            "announcement": (None, forms.AnnouncementForm),
        }
        if kind not in definitions:
            raise NotFoundError()
        permissions = {
            "details": "lms.course.manage",
            "material": "lms.material.manage",
            "assignment": "lms.assignment.manage",
            "announcement": "lms.announcement.create",
        }
        workspace, _context = services.workspace_context(
            request.principal,
            pk,
            ("faculty", "ta") if kind == "announcement" else ("faculty",),
            permissions[kind],
        )
        model, form_class = definitions[kind]
        instance = workspace if kind == "details" else None
        if item_id and model:
            instance = model.objects.filter(pk=item_id, workspace=workspace).first()
            if instance is None:
                raise NotFoundError()
        form = form_class(request.data, request.FILES, instance=instance)
        if not form.is_valid():
            raise DomainError(
                "Check the submitted fields.",
                details=[{"field": k, "message": " ".join(v)} for k, v in form.errors.items()],
            )
        try:
            obj = services.save_content(
                request.principal, pk, kind, dict(form.cleaned_data), item_id
            )
        except ValidationError as exc:
            raise DomainError("; ".join(exc.messages)) from exc
        return Response({"id": obj.pk}, status=200 if item_id or kind == "details" else 201)


class UpdateContent(WriteContent):
    @extend_schema(
        operation_id="lms_content_update",
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, pk, kind, item_id=None):
        return super().post(request, pk, kind, item_id)


class Publish(LmsView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk, item_id):
        obj = services.publish_assignment(request.principal, pk, item_id)
        return Response(s.AssignmentSerializer(obj).data)


class Submit(LmsView):
    @extend_schema(request=OpenApiTypes.OBJECT, responses=s.SubmissionSerializer)
    def post(self, request, pk, item_id):
        form = forms.SubmissionForm(request.data, request.FILES)
        if not form.is_valid():
            raise DomainError("Provide valid submission content.")
        row = services.submit(request.principal, pk, item_id, form.cleaned_data)
        return Response(s.SubmissionSerializer(row).data, status=201)


class Grade(LmsView):
    @extend_schema(request=OpenApiTypes.OBJECT, responses=s.SubmissionSerializer)
    def post(self, request, pk, item_id):
        form = forms.GradeForm(request.data)
        if not form.is_valid():
            raise DomainError("Provide valid points, feedback and revision.")
        row = services.grade(request.principal, pk, item_id, form.cleaned_data)
        return Response(s.SubmissionSerializer(row, context={"reviewer": True}).data)


class Release(LmsView):
    @extend_schema(request=s.RevisionSerializer, responses=s.SubmissionSerializer)
    def post(self, request, pk, item_id):
        payload = s.RevisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.grade(request.principal, pk, item_id, payload.validated_data, release=True)
        return Response(s.SubmissionSerializer(row, context={"reviewer": True}).data)


class Download(LmsView):
    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    def get(self, request, pk, kind, item_id):
        workspace, context = services.workspace_context(request.principal, pk)
        services.release_due()
        role = context["role"]
        if kind == "material":
            obj = q.materials(workspace, role).filter(pk=item_id).first()
        elif kind == "assignment":
            obj = q.assignments(workspace, role).filter(pk=item_id).first()
            if obj and not obj.file:
                response = HttpResponse(obj.instructions, content_type="text/plain; charset=utf-8")
                response["Content-Disposition"] = 'attachment; filename="assignment.txt"'
                return response
        elif kind == "submission":
            obj = (
                q.submissions(workspace, role, request.principal.user_id).filter(pk=item_id).first()
            )
        else:
            raise NotFoundError()
        if obj is None or not obj.file:
            raise NotFoundError()
        response = FileResponse(obj.file.open("rb"), as_attachment=True, filename="course-file")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
