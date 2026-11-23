import io

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework.response import Response

from core.api.exceptions import NotFoundError
from core.files.writers import stream_upload
from modules.lms.api import serializers as s
from modules.lms.api.base import LmsView
from modules.lms.api.examples import examples_for
from modules.lms.selectors import scoping
from modules.lms.selectors.workspaces import course_data, course_rows
from modules.lms.services import (
    announcements,
    assignments,
    grading,
    materials,
    releases,
    submissions,
)
from modules.lms.services import workspaces as workspace_services


@extend_schema_view(
    get=extend_schema(
        responses=s.CourseSerializer(many=True),
        examples=examples_for(None, s.CourseSerializer, 200),
    )
)
class Courses(LmsView):
    serializer_class = s.CourseSerializer
    permission_map = {"GET": "lms.course.view"}

    def get(self, request):
        page = self.paginate_queryset(course_rows(self.scope).order_by("-id"))
        return self.get_paginated_response(
            s.CourseSerializer(course_data(page, self.scope), many=True).data
        )


@extend_schema_view(
    get=extend_schema(
        responses=s.CourseSerializer, examples=examples_for(None, s.CourseSerializer, 200)
    ),
    patch=extend_schema(
        request=s.CourseInput,
        responses=s.CourseSerializer,
        examples=examples_for(s.CourseInput, s.CourseSerializer, 200),
    ),
)
class CourseDetail(LmsView):
    serializer_class = s.CourseSerializer
    permission_map = {"GET": "lms.course.view", "PATCH": "lms.course.update"}

    def get(self, request, pk):
        row = get_object_or_404(course_rows(self.scope), pk=pk)
        return Response(s.CourseSerializer(course_data([row], self.scope)[0]).data)

    def patch(self, request, pk):
        workspace_services.update_details(self.scope, pk, self.inputs(s.CourseInput))
        return self.get(request, pk)


@extend_schema_view(
    get=extend_schema(
        responses=s.PolicySerializer, examples=examples_for(None, s.PolicySerializer, 200)
    )
)
class Policy(LmsView):
    serializer_class = s.PolicySerializer
    permission_map = {"GET": "lms.course_policy.view"}

    def get(self, request, pk):
        scoping.workspace(self.scope, pk)
        row = scoping.effective_policy(pk)
        return Response(
            s.PolicySerializer(row).data
            if row
            else {
                "id": None,
                "workspace_id": pk,
                "effective_from": None,
                "author_user_id": None,
                "decision_version": "A9-LMS-BP-0.2",
                "version": 0,
                "can_ta_post_announcements": False,
            }
        )


@extend_schema_view(
    post=extend_schema(
        request=s.PolicyInput,
        responses={201: s.PolicySerializer},
        examples=examples_for(s.PolicyInput, s.PolicySerializer, 201),
    )
)
class PolicyVersions(LmsView):
    serializer_class = s.PolicySerializer
    permission_map = {"POST": "lms.course_policy.update"}

    def post(self, request, pk):
        row = workspace_services.set_policy(self.scope, pk, self.inputs(s.PolicyInput))
        return Response(s.PolicySerializer(row).data, status=201)


@extend_schema_view(
    post=extend_schema(
        request=s.SectionInput,
        responses={201: s.SectionSerializer},
        examples=examples_for(s.SectionInput, s.SectionSerializer, 201),
    )
)
class Sections(LmsView):
    serializer_class = s.SectionSerializer
    permission_map = {"POST": "lms.section.create"}

    def post(self, request, pk):
        row = workspace_services.save_section(
            self.scope, self.inputs(s.SectionInput), workspace_id=pk
        )
        return Response(s.SectionSerializer(row).data, status=201)


@extend_schema_view(
    patch=extend_schema(
        request=s.SectionInput,
        responses=s.SectionSerializer,
        examples=examples_for(s.SectionInput, s.SectionSerializer, 200),
    )
)
class SectionDetail(LmsView):
    serializer_class = s.SectionSerializer
    permission_map = {"PATCH": "lms.section.update"}

    def patch(self, request, pk):
        row = workspace_services.save_section(
            self.scope, self.inputs(s.SectionInput, partial=True), pk=pk
        )
        return Response(s.SectionSerializer(row).data)


@extend_schema_view(
    get=extend_schema(
        responses=s.MaterialSerializer(many=True),
        examples=examples_for(None, s.MaterialSerializer, 200),
    ),
    post=extend_schema(
        request=s.MaterialInput,
        responses={201: s.MaterialSerializer},
        examples=examples_for(s.MaterialInput, s.MaterialSerializer, 201),
    ),
)
class Materials(LmsView):
    serializer_class = s.MaterialSerializer
    permission_map = {"GET": "lms.material.view", "POST": "lms.material.create"}

    def get(self, request, pk):
        scoping.workspace(self.scope, pk)
        return self.listing(
            scoping.materials(self.scope).filter(workspace_id=pk), s.MaterialSerializer
        )

    def post(self, request, pk):
        row = materials.save_material(self.scope, self.inputs(s.MaterialInput), workspace_id=pk)
        return Response(s.MaterialSerializer(row).data, status=201)


@extend_schema_view(
    get=extend_schema(
        responses=s.MaterialSerializer, examples=examples_for(None, s.MaterialSerializer, 200)
    ),
    patch=extend_schema(
        request=s.MaterialInput,
        responses=s.MaterialSerializer,
        examples=examples_for(s.MaterialInput, s.MaterialSerializer, 200),
    ),
)
class MaterialDetail(LmsView):
    serializer_class = s.MaterialSerializer
    permission_map = {"GET": "lms.material.view", "PATCH": "lms.material.update"}

    def get(self, request, pk):
        return Response(
            s.MaterialSerializer(get_object_or_404(scoping.materials(self.scope), pk=pk)).data
        )

    def patch(self, request, pk):
        row = materials.save_material(self.scope, self.inputs(s.MaterialInput, partial=True), pk=pk)
        return Response(s.MaterialSerializer(row).data)


@extend_schema_view(
    post=extend_schema(
        request=s.ReleaseInput,
        responses=s.MaterialSerializer,
        examples=examples_for(s.ReleaseInput, s.MaterialSerializer, 200),
    )
)
class MaterialPublish(LmsView):
    serializer_class = s.MaterialSerializer
    permission_map = {"POST": "lms.material.publish"}

    def post(self, request, pk):
        row = releases.change_release(self.scope, "material", pk, **self.inputs(s.ReleaseInput))
        return Response(s.MaterialSerializer(row).data)


@extend_schema_view(
    post=extend_schema(
        request=s.EmptyInput,
        responses=s.MaterialSerializer,
        examples=examples_for(s.EmptyInput, s.MaterialSerializer, 200),
    )
)
class MaterialWithdraw(LmsView):
    serializer_class = s.MaterialSerializer
    permission_map = {"POST": "lms.material.publish"}

    def post(self, request, pk):
        self.inputs(s.EmptyInput)
        return Response(
            s.MaterialSerializer(
                releases.change_release(self.scope, "material", pk, withdraw=True)
            ).data
        )


def download_file(row):
    if row.stored_file is None:
        raise NotFoundError("This item does not contain a file.")
    return stream_upload(
        row.stored_file.storage_key, name=row.stored_file.name, mime_type=row.stored_file.mime_type
    )


@extend_schema_view(
    get=extend_schema(
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        examples=[
            OpenApiExample(
                "Private attachment",
                value="Validated attachment bytes",
                media_type="application/octet-stream",
                response_only=True,
            )
        ],
    )
)
class MaterialDownload(LmsView):
    serializer_class = s.MaterialSerializer
    permission_map = {"GET": "lms.material.view"}

    def get(self, request, pk):
        return download_file(get_object_or_404(scoping.materials(self.scope), pk=pk))


@extend_schema_view(
    get=extend_schema(
        responses=s.AnnouncementSerializer(many=True),
        examples=examples_for(None, s.AnnouncementSerializer, 200),
    ),
    post=extend_schema(
        request=s.AnnouncementInput,
        responses={201: s.AnnouncementSerializer},
        examples=examples_for(s.AnnouncementInput, s.AnnouncementSerializer, 201),
    ),
)
class Announcements(LmsView):
    serializer_class = s.AnnouncementSerializer
    permission_map = {"GET": "lms.announcement.view", "POST": "lms.announcement.create"}

    def get(self, request, pk):
        scoping.workspace(self.scope, pk)
        return self.listing(
            scoping.announcements(self.scope).filter(workspace_id=pk), s.AnnouncementSerializer
        )

    def post(self, request, pk):
        row = announcements.post_announcement(self.scope, pk, **self.inputs(s.AnnouncementInput))
        return Response(s.AnnouncementSerializer(row).data, status=201)


@extend_schema_view(
    get=extend_schema(
        responses=s.AssignmentSerializer(many=True),
        examples=examples_for(None, s.AssignmentSerializer, 200),
    ),
    post=extend_schema(
        request=s.AssignmentInput,
        responses={201: s.AssignmentSerializer},
        examples=examples_for(s.AssignmentInput, s.AssignmentSerializer, 201),
    ),
)
class Assignments(LmsView):
    serializer_class = s.AssignmentSerializer
    permission_map = {"GET": "lms.assignment.view", "POST": "lms.assignment.create"}

    def get(self, request, pk):
        scoping.workspace(self.scope, pk)
        return self.listing(
            scoping.assignments(self.scope).filter(workspace_id=pk), s.AssignmentSerializer
        )

    def post(self, request, pk):
        row = assignments.save_assignment(
            self.scope, self.inputs(s.AssignmentInput), workspace_id=pk
        )
        return Response(s.AssignmentSerializer(row).data, status=201)


@extend_schema_view(
    get=extend_schema(
        responses=s.AssignmentSerializer, examples=examples_for(None, s.AssignmentSerializer, 200)
    ),
    patch=extend_schema(
        request=s.AssignmentInput,
        responses=s.AssignmentSerializer,
        examples=examples_for(s.AssignmentInput, s.AssignmentSerializer, 200),
    ),
)
class AssignmentDetail(LmsView):
    serializer_class = s.AssignmentSerializer
    permission_map = {"GET": "lms.assignment.view", "PATCH": "lms.assignment.update"}

    def get(self, request, pk):
        return Response(
            s.AssignmentSerializer(get_object_or_404(scoping.assignments(self.scope), pk=pk)).data
        )

    def patch(self, request, pk):
        row = assignments.save_assignment(
            self.scope, self.inputs(s.AssignmentInput, partial=True), pk=pk
        )
        return Response(s.AssignmentSerializer(row).data)


@extend_schema_view(
    post=extend_schema(
        request=s.ReleaseInput,
        responses=s.AssignmentSerializer,
        examples=examples_for(s.ReleaseInput, s.AssignmentSerializer, 200),
    )
)
class AssignmentPublish(LmsView):
    serializer_class = s.AssignmentSerializer
    permission_map = {"POST": "lms.assignment.publish"}

    def post(self, request, pk):
        return Response(
            s.AssignmentSerializer(
                releases.change_release(self.scope, "assignment", pk, **self.inputs(s.ReleaseInput))
            ).data
        )


@extend_schema_view(
    post=extend_schema(
        request=s.EmptyInput,
        responses=s.AssignmentSerializer,
        examples=examples_for(s.EmptyInput, s.AssignmentSerializer, 200),
    )
)
class AssignmentWithdraw(LmsView):
    serializer_class = s.AssignmentSerializer
    permission_map = {"POST": "lms.assignment.publish"}

    def post(self, request, pk):
        self.inputs(s.EmptyInput)
        return Response(
            s.AssignmentSerializer(
                releases.change_release(self.scope, "assignment", pk, withdraw=True)
            ).data
        )


@extend_schema_view(
    get=extend_schema(
        responses={(200, "text/plain"): OpenApiTypes.BINARY},
        examples=[
            OpenApiExample(
                "Assignment instructions",
                value="Exercise\nExplain the result\n",
                media_type="text/plain",
                response_only=True,
            )
        ],
    )
)
class AssignmentDownload(LmsView):
    serializer_class = s.AssignmentSerializer
    permission_map = {"GET": "lms.assignment.view"}

    def get(self, request, pk):
        row = get_object_or_404(scoping.assignments(self.scope), pk=pk)
        content = (
            f"{row.title}\n{row.instructions}\nDue: {row.due_at.isoformat()}\n"
            f"Type: {row.submission_type}\nPoints: {row.points_possible}\n"
        ).encode()
        response = FileResponse(
            io.BytesIO(content),
            as_attachment=True,
            filename=f"assignment-{row.pk}.txt",
            content_type="text/plain",
        )
        response["Cache-Control"] = "private, no-store"
        return response


@extend_schema_view(
    get=extend_schema(
        responses=s.SubmissionSerializer(many=True),
        examples=examples_for(None, s.SubmissionSerializer, 200),
    ),
    post=extend_schema(
        request=s.SubmissionInput,
        responses={201: s.SubmissionSerializer},
        examples=examples_for(s.SubmissionInput, s.SubmissionSerializer, 201),
    ),
)
class Submissions(LmsView):
    serializer_class = s.SubmissionSerializer
    permission_map = {"GET": "lms.submission.view", "POST": "lms.submission.create"}

    def get(self, request, pk):
        get_object_or_404(scoping.assignments(self.scope), pk=pk)
        return self.listing(
            scoping.submissions(self.scope).filter(assignment_id=pk), s.SubmissionSerializer
        )

    def post(self, request, pk):
        row = submissions.create_submission(self.scope, pk, self.inputs(s.SubmissionInput))
        return Response(s.SubmissionSerializer(row).data, status=201)


@extend_schema_view(
    get=extend_schema(
        responses=s.SubmissionSerializer, examples=examples_for(None, s.SubmissionSerializer, 200)
    )
)
class SubmissionDetail(LmsView):
    serializer_class = s.SubmissionSerializer
    permission_map = {"GET": "lms.submission.view"}

    def get(self, request, pk):
        return Response(
            s.SubmissionSerializer(get_object_or_404(scoping.submissions(self.scope), pk=pk)).data
        )


@extend_schema_view(
    get=extend_schema(
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        examples=[
            OpenApiExample(
                "Private attachment",
                value="Validated attachment bytes",
                media_type="application/octet-stream",
                response_only=True,
            )
        ],
    )
)
class SubmissionDownload(LmsView):
    serializer_class = s.SubmissionSerializer
    permission_map = {"GET": "lms.submission.view"}

    def get(self, request, pk):
        return download_file(get_object_or_404(scoping.submissions(self.scope), pk=pk))


@extend_schema_view(
    post=extend_schema(
        request=s.GradeInput,
        responses=s.GradeSerializer,
        examples=examples_for(s.GradeInput, s.GradeSerializer, 200),
    ),
    patch=extend_schema(
        request=s.GradeInput,
        responses=s.GradeSerializer,
        examples=examples_for(s.GradeInput, s.GradeSerializer, 200),
    ),
)
class SubmissionGrade(LmsView):
    serializer_class = s.GradeSerializer
    permission_map = {"POST": "lms.grade.create", "PATCH": "lms.grade.update"}

    def post(self, request, pk):
        return Response(
            s.GradeSerializer(grading.save_grade(self.scope, pk, self.inputs(s.GradeInput))).data
        )

    def patch(self, request, pk):
        return self.post(request, pk)


@extend_schema_view(
    post=extend_schema(
        request=s.EmptyInput,
        responses=s.GradeSerializer,
        examples=examples_for(s.EmptyInput, s.GradeSerializer, 200),
    )
)
class GradeRelease(LmsView):
    serializer_class = s.GradeSerializer
    permission_map = {"POST": "lms.grade.publish"}

    def post(self, request, pk):
        self.inputs(s.EmptyInput)
        return Response(s.GradeSerializer(grading.release_grade(self.scope, pk)).data)


@extend_schema_view(
    get=extend_schema(
        responses=s.GradeSerializer(many=True), examples=examples_for(None, s.GradeSerializer, 200)
    )
)
class Grades(LmsView):
    serializer_class = s.GradeSerializer
    permission_map = {"GET": "lms.grade.view"}

    def get(self, request, pk):
        scoping.workspace(self.scope, pk)
        return self.listing(
            scoping.grades(self.scope).filter(submission__assignment__workspace_id=pk),
            s.GradeSerializer,
        )
