from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from modules.lms.models import (
    Course,
    CourseMembership,
    CourseMaterial,
    CourseAnnouncement,
    Assignment,
    AssignmentSubmission,
    SubmissionGrade,
    GradeChangeAudit,
)


class CourseMembershipSerializer(serializers.ModelSerializer):
    user_display_name = serializers.CharField(read_only=True, default="")
    user_email = serializers.CharField(read_only=True, default="")

    class Meta:
        model = CourseMembership
        fields = [
            "id",
            "course",
            "user_id",
            "role",
            "is_primary_instructor",
            "is_active",
            "user_display_name",
            "user_email",
            "created_at",
        ]
        read_only_fields = ["course", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    my_role = serializers.CharField(read_only=True, default="")
    instructors = serializers.SerializerMethodField()
    tas = serializers.SerializerMethodField()
    materials_count = serializers.IntegerField(read_only=True, default=0)
    assignments_count = serializers.IntegerField(read_only=True, default=0)
    announcements_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "name",
            "academic_year",
            "semester",
            "syllabus",
            "schedule",
            "allow_ta_announcements",
            "allow_ta_grading",
            "is_active",
            "created_at",
            "updated_at",
            "my_role",
            "instructors",
            "tas",
            "materials_count",
            "assignments_count",
            "announcements_count",
        ]

    def get_instructors(self, obj) -> list[dict]:
        members = obj.memberships.filter(role="faculty", is_active=True)
        return [
            {
                "user_id": m.user_id,
                "is_primary": m.is_primary_instructor,
            }
            for m in members
        ]

    def get_tas(self, obj) -> list[dict]:
        members = obj.memberships.filter(role="ta", is_active=True)
        return [
            {
                "user_id": m.user_id,
            }
            for m in members
        ]


class CourseMaterialSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = CourseMaterial
        fields = [
            "id",
            "course",
            "title",
            "material_type",
            "section",
            "content",
            "link_url",
            "file_name",
            "file_size",
            "status",
            "release_date",
            "created_by_user_id",
            "created_at",
            "updated_at",
            "is_available",
        ]
        read_only_fields = ["course", "created_by_user_id", "created_at", "updated_at", "file_size"]

    def get_is_available(self, obj) -> bool:
        return obj.is_available()

    def validate(self, attrs):
        m_type = attrs.get("material_type", getattr(self.instance, "material_type", None))
        if m_type == "link" and not attrs.get("link_url") and not (self.instance and self.instance.link_url):
            raise serializers.ValidationError({"link_url": "Link URL is required for link materials."})
        if m_type == "note" and not attrs.get("content") and not (self.instance and self.instance.content):
            raise serializers.ValidationError({"content": "Content is required for note materials."})
        return attrs


class CourseAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAnnouncement
        fields = [
            "id",
            "course",
            "title",
            "content",
            "posted_by_user_id",
            "posted_by_role",
            "posted_by_name",
            "is_pinned",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "course",
            "posted_by_user_id",
            "posted_by_role",
            "posted_by_name",
            "created_at",
            "updated_at",
        ]


class GradeChangeAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeChangeAudit
        fields = [
            "id",
            "grade",
            "previous_points",
            "new_points",
            "previous_feedback",
            "new_feedback",
            "changed_by_user_id",
            "changed_by_name",
            "change_reason",
            "changed_at",
        ]
        read_only_fields = ["grade", "changed_at"]


class SubmissionGradeSerializer(serializers.ModelSerializer):
    audit_logs = GradeChangeAuditSerializer(many=True, read_only=True)

    class Meta:
        model = SubmissionGrade
        fields = [
            "id",
            "submission",
            "points_awarded",
            "feedback",
            "status",
            "graded_by_user_id",
            "graded_by_role",
            "graded_by_name",
            "released_at",
            "released_by_user_id",
            "created_at",
            "updated_at",
            "audit_logs",
        ]
        read_only_fields = [
            "submission",
            "graded_by_user_id",
            "graded_by_role",
            "graded_by_name",
            "released_at",
            "released_by_user_id",
            "created_at",
            "updated_at",
        ]


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    assignment_points_possible = serializers.DecimalField(
        source="assignment.points_possible", max_digits=6, decimal_places=2, read_only=True
    )
    grade = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentSubmission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "assignment_points_possible",
            "student_user_id",
            "submission_type",
            "text_response",
            "link_url",
            "file_name",
            "submitted_at",
            "status",
            "version",
            "created_at",
            "updated_at",
            "grade",
        ]
        read_only_fields = [
            "assignment",
            "student_user_id",
            "submitted_at",
            "status",
            "version",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.DictField)
    def get_grade(self, obj):
        if not hasattr(obj, "grade") or obj.grade is None:
            return None
        # BR-LMS-016: If grade is draft, only return to faculty/ta, hide from student
        request = self.context.get("request")
        user_id = getattr(getattr(request, "principal", None), "user_id", None)
        is_student = (user_id == obj.student_user_id)
        if is_student and obj.grade.status == "draft":
            return None
        return SubmissionGradeSerializer(obj.grade).data


class AssignmentSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    is_available = serializers.SerializerMethodField()
    my_submission = serializers.SerializerMethodField()
    submissions_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "course_code",
            "course_name",
            "title",
            "instructions",
            "submission_type",
            "points_possible",
            "due_date",
            "release_date",
            "status",
            "allow_late_submissions",
            "created_by_user_id",
            "created_at",
            "updated_at",
            "is_available",
            "my_submission",
            "submissions_count",
        ]
        read_only_fields = ["course", "created_by_user_id", "created_at", "updated_at"]

    def get_is_available(self, obj) -> bool:
        return obj.is_available_to_students()

    @extend_schema_field(serializers.DictField)
    def get_my_submission(self, obj):
        request = self.context.get("request")
        user_id = getattr(getattr(request, "principal", None), "user_id", None)
        if not user_id:
            return None
        sub = obj.submissions.filter(student_user_id=user_id).order_by("-submitted_at").first()
        if not sub:
            return None
        return AssignmentSubmissionSerializer(sub, context=self.context).data

    def validate(self, attrs):
        # BR-LMS-009: Required configuration: due_date, instructions, submission_type, points_possible
        due_date = attrs.get("due_date", getattr(self.instance, "due_date", None))
        instructions = attrs.get("instructions", getattr(self.instance, "instructions", None))
        submission_type = attrs.get("submission_type", getattr(self.instance, "submission_type", None))
        points = attrs.get("points_possible", getattr(self.instance, "points_possible", None))

        if not due_date:
            raise serializers.ValidationError({"due_date": "Due date is required."})
        if not instructions or not instructions.strip():
            raise serializers.ValidationError({"instructions": "Instructions are required."})
        if not submission_type:
            raise serializers.ValidationError({"submission_type": "Submission type is required."})
        if points is None or points <= 0:
            raise serializers.ValidationError({"points_possible": "Points possible must be greater than zero."})

        return attrs
