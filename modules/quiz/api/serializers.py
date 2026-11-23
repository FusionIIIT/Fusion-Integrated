"""Explicit Quiz request and response shapes; Student fields are key-free."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.quiz.domain.quiz_definition import QuizDefinition
from modules.quiz.models import Question, QuestionOption, Quiz


class QuizDraftCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=250)
    course_id = serializers.IntegerField(min_value=1)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    duration_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    maximum_marks = serializers.DecimalField(
        max_digits=9, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    passing_marks = serializers.DecimalField(
        max_digits=9, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    permitted_attempts = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    close_at = serializers.DateTimeField(required=False, allow_null=True)

    @staticmethod
    def definition(data: dict[str, Any]) -> QuizDefinition:
        return QuizDefinition(
            title=data["title"],
            course_id=data["course_id"],
            duration_seconds=data.get("duration_seconds"),
            maximum_marks=data.get("maximum_marks"),
            passing_marks=data.get("passing_marks"),
            permitted_attempts=data.get("permitted_attempts"),
            start_at=data.get("start_at"),
            close_at=data.get("close_at"),
        )


class QuizDraftUpdateSerializer(serializers.Serializer):
    """Full definition replacement; nullable settings must be explicit."""

    title = serializers.CharField(max_length=250)
    course_id = serializers.IntegerField(min_value=1)
    duration_seconds = serializers.IntegerField(allow_null=True, min_value=1)
    maximum_marks = serializers.DecimalField(
        max_digits=9, decimal_places=2, allow_null=True, min_value=0
    )
    passing_marks = serializers.DecimalField(
        max_digits=9, decimal_places=2, allow_null=True, min_value=0
    )
    permitted_attempts = serializers.IntegerField(allow_null=True, min_value=1)
    start_at = serializers.DateTimeField(allow_null=True)
    close_at = serializers.DateTimeField(allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField(required=False, allow_blank=True)

    @staticmethod
    def definition(data: dict[str, Any]) -> QuizDefinition:
        return QuizDefinition(
            title=data["title"],
            course_id=data["course_id"],
            duration_seconds=data["duration_seconds"],
            maximum_marks=data["maximum_marks"],
            passing_marks=data["passing_marks"],
            permitted_attempts=data["permitted_attempts"],
            start_at=data["start_at"],
            close_at=data["close_at"],
        )


class QuizPublishSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("publish_now", "schedule"))


class QuizDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = (
            "public_id",
            "course_id",
            "title",
            "description",
            "instructions",
            "duration_seconds",
            "maximum_marks",
            "passing_marks",
            "permitted_attempts",
            "status",
            "start_at",
            "close_at",
            "question_selection_mode",
            "sample_count",
            "shuffle_questions",
            "shuffle_options",
            "back_navigation_allowed",
            "one_question_at_a_time",
            "unanswered_allowed",
            "tab_block_enabled",
            "negative_marking_enabled",
        )
        read_only_fields = fields


class EligibleQuizSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    attempts_started = serializers.IntegerField(read_only=True)
    attempts_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = (
            "public_id",
            "title",
            "description",
            "instructions",
            "duration_seconds",
            "maximum_marks",
            "passing_marks",
            "permitted_attempts",
            "start_at",
            "close_at",
            "question_count",
            "attempts_started",
            "attempts_remaining",
        )
        read_only_fields = fields

    def get_attempts_remaining(self, quiz: Quiz) -> int:
        return max(0, (quiz.permitted_attempts or 0) - quiz.attempts_started)


class QuestionOptionOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ("option_key", "text", "is_correct", "position")
        read_only_fields = fields


class QuestionBankOwnerSerializer(serializers.ModelSerializer):
    options = QuestionOptionOwnerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "public_id",
            "subject_id",
            "question_type",
            "prompt",
            "marks",
            "negative_mark_value",
            "topic",
            "difficulty",
            "answer_key",
            "reference_answer",
            "evaluation_criteria",
            "options",
        )
        read_only_fields = fields


class QuestionBankSearchSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField(required=False, min_value=1)
    topic = serializers.CharField(required=False, allow_blank=False, max_length=160)
    difficulty = serializers.CharField(required=False, allow_blank=False, max_length=24)
    question_type = serializers.ChoiceField(
        required=False,
        choices=(
            "multiple_choice",
            "multiple_select",
            "true_false",
            "fill_blank",
            "short_answer",
            "long_answer",
        ),
    )


class StudentOptionSerializer(serializers.Serializer):
    option_key = serializers.UUIDField()
    text = serializers.CharField()


class StudentAttemptItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_order = serializers.IntegerField()
    question_id = serializers.UUIDField()
    question_type = serializers.CharField()
    prompt = serializers.CharField()
    marks = serializers.DecimalField(max_digits=9, decimal_places=2)
    displayed_option_keys = serializers.ListField(child=serializers.UUIDField())
    options = StudentOptionSerializer(many=True)
    answer_payload = serializers.JSONField(allow_null=True)
    revision = serializers.IntegerField(allow_null=True)
    saved_at = serializers.DateTimeField(allow_null=True)


class StudentAttemptSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField(source="pk")
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    deadline_at = serializers.DateTimeField()
    submitted_at = serializers.DateTimeField(allow_null=True)
    quiz_public_id = serializers.UUIDField(source="quiz.public_id")
    quiz_title = serializers.CharField(source="quiz.title")
    items = serializers.SerializerMethodField()

    @extend_schema_field(StudentAttemptItemSerializer(many=True))
    def get_items(self, _attempt) -> list[dict[str, Any]]:
        grouped: OrderedDict[int, dict[str, Any]] = OrderedDict()
        for row in self.context["presentation_rows"]:
            item = grouped.setdefault(
                row["id"],
                {
                    "id": row["id"],
                    "display_order": row["display_order"],
                    "question_id": row["question__public_id"],
                    "question_type": row["question__question_type"],
                    "prompt": row["question__prompt"],
                    "marks": row["marks_at_start"],
                    "displayed_option_keys": row["displayed_option_keys"],
                    "options": [],
                    "answer_payload": row["response__answer_payload"],
                    "revision": row["response__revision"],
                    "saved_at": row["response__saved_at"],
                },
            )
            option_key = row["question__options__option_key"]
            if option_key is not None:
                item["options"].append(
                    {"option_key": option_key, "text": row["question__options__text"]}
                )

        result = list(grouped.values())
        for item in result:
            order = [str(key) for key in item["displayed_option_keys"]]
            order_index = {key: index for index, key in enumerate(order)}
            item["options"] = [
                option for option in item["options"] if str(option["option_key"]) in order_index
            ]
            item["options"].sort(key=lambda option: order_index[str(option["option_key"])])
        return StudentAttemptItemSerializer(result, many=True).data


class SaveResponseSerializer(serializers.Serializer):
    answer_payload = serializers.JSONField(allow_null=True)
    expected_revision = serializers.IntegerField(min_value=0)


class ResponseSavedSerializer(serializers.Serializer):
    attempt_question_id = serializers.IntegerField()
    revision = serializers.IntegerField()
    saved_at = serializers.DateTimeField()


class SubmitAttemptSerializer(serializers.Serializer):
    confirmed = serializers.BooleanField()

    def validate_confirmed(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("Explicit submission confirmation is required.")
        return value


class AttemptSubmissionResponseSerializer(serializers.Serializer):
    """Successful manual submission response returned by the attempt API."""

    attempt_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=("submitted",))
    submitted_at = serializers.DateTimeField()


class ReleasedResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    total_marks = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    marks_obtained = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    percentage = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    correct_count = serializers.IntegerField(allow_null=True)
    incorrect_count = serializers.IntegerField(allow_null=True)
    unanswered_count = serializers.IntegerField(allow_null=True)
    passed = serializers.BooleanField(allow_null=True)
    released_at = serializers.DateTimeField(allow_null=True)
    attempt_number = serializers.IntegerField(source="attempt__attempt_number")
    started_at = serializers.DateTimeField(source="attempt__started_at")
    submitted_at = serializers.DateTimeField(source="attempt__submitted_at", allow_null=True)
    quiz_public_id = serializers.UUIDField(source="attempt__quiz__public_id")
    quiz_title = serializers.CharField(source="attempt__quiz__title")
