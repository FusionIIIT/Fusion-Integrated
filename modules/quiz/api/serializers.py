"""Quiz API serializers — explicit allow-lists, never fields='__all__'."""
from decimal import Decimal

from rest_framework import serializers

from modules.quiz.models import AttemptResponse, Question, Quiz, QuizAttempt

# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

class QuizListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""
    question_count = serializers.IntegerField(read_only=True, default=0)
    attempt_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Quiz
        fields = (
            "id", "title", "description", "course", "status",
            "duration_minutes", "max_marks", "passing_marks", "max_attempts",
            "start_at", "close_at", "result_visibility",
            "question_count", "attempt_count",
            "created_by_user_id", "created_at", "updated_at",
        )
        read_only_fields = fields


class QuizDetailSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True, default=0)
    attempt_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Quiz
        fields = (
            "id", "title", "description", "course", "instructions", "status",
            "duration_minutes", "max_marks", "passing_marks", "max_attempts",
            "start_at", "close_at",
            "allow_back_navigation", "one_question_at_a_time",
            "randomize_questions", "randomize_options",
            "allow_unanswered", "tab_block", "negative_marking",
            "result_visibility",
            "question_count", "attempt_count",
            "created_by_user_id", "created_at", "updated_at",
        )
        read_only_fields = fields


class QuizWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    course = serializers.CharField(max_length=200)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    duration_minutes = serializers.IntegerField(min_value=1)
    max_marks = serializers.DecimalField(max_digits=8, decimal_places=2)
    passing_marks = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    max_attempts = serializers.IntegerField(min_value=1, default=1)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    close_at = serializers.DateTimeField(required=False, allow_null=True)
    allow_back_navigation = serializers.BooleanField(required=False, default=True)
    one_question_at_a_time = serializers.BooleanField(required=False, default=False)
    randomize_questions = serializers.BooleanField(required=False, default=False)
    randomize_options = serializers.BooleanField(required=False, default=False)
    allow_unanswered = serializers.BooleanField(required=False, default=True)
    tab_block = serializers.BooleanField(required=False, default=False)
    negative_marking = serializers.BooleanField(required=False, default=False)
    result_visibility = serializers.ChoiceField(
        choices=Quiz.RESULT_VISIBILITY_CHOICES,
        required=False, default="after_release",
    )


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = (
            "id", "quiz", "question_type", "text", "image_url",
            "marks", "negative_marks", "topic", "difficulty", "order",
            "is_bank_question", "options", "correct_answer",
            "reference_answer", "evaluation_criteria",
        )
        read_only_fields = ("id", "quiz")


class QuestionWriteSerializer(serializers.Serializer):
    question_type = serializers.ChoiceField(
        choices=["mcq", "msq", "tf", "fitb", "short"]
    )
    text = serializers.CharField()
    image_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    negative_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, default=Decimal("0")
    )
    topic = serializers.CharField(required=False, allow_blank=True, default="")
    difficulty = serializers.ChoiceField(
        choices=["easy", "medium", "hard", ""],
        required=False, allow_blank=True, default=""
    )
    order = serializers.IntegerField(required=False, default=0)
    is_bank_question = serializers.BooleanField(required=False, default=False)
    options = serializers.JSONField(required=False, allow_null=True)
    correct_answer = serializers.JSONField(required=False, allow_null=True)
    reference_answer = serializers.CharField(required=False, allow_blank=True, default="")
    evaluation_criteria = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Attempt
# ---------------------------------------------------------------------------

class AttemptResponseSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text", read_only=True)
    question_type = serializers.CharField(source="question.question_type", read_only=True)
    marks = serializers.DecimalField(
        source="question.marks", max_digits=6, decimal_places=2, read_only=True
    )
    options = serializers.JSONField(source="question.options", read_only=True)
    correct_answer = serializers.JSONField(source="question.correct_answer", read_only=True)

    class Meta:
        model = AttemptResponse
        fields = (
            "id", "question", "question_text", "question_type", "marks",
            "options", "correct_answer",
            "response", "is_correct", "marks_obtained",
            "ai_suggested_marks", "ai_reasoning", "professor_feedback",
            "evaluated_at",
        )
        read_only_fields = fields


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_course = serializers.CharField(source="quiz.course", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            "id", "quiz", "quiz_title", "quiz_course",
            "user_id", "status", "started_at", "submitted_at",
            "attempt_number", "score", "percentage", "passed",
            "time_taken_seconds", "tab_violations", "created_at",
        )
        read_only_fields = fields


class AttemptDetailSerializer(serializers.ModelSerializer):
    """Full attempt with questions and responses for the quiz-taking UI."""
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_course = serializers.CharField(source="quiz.course", read_only=True)
    questions = QuestionSerializer(source="quiz.questions", many=True, read_only=True)
    responses = AttemptResponseSerializer(many=True, read_only=True)
    time_remaining_seconds = serializers.SerializerMethodField()

    # Quiz config fields needed by the frontend
    duration_minutes = serializers.IntegerField(source="quiz.duration_minutes", read_only=True)
    allow_back_navigation = serializers.BooleanField(
        source="quiz.allow_back_navigation", read_only=True
    )
    one_question_at_a_time = serializers.BooleanField(
        source="quiz.one_question_at_a_time", read_only=True
    )
    randomize_questions = serializers.BooleanField(
        source="quiz.randomize_questions", read_only=True
    )
    allow_unanswered = serializers.BooleanField(
        source="quiz.allow_unanswered", read_only=True
    )
    tab_block = serializers.BooleanField(source="quiz.tab_block", read_only=True)
    instructions = serializers.CharField(source="quiz.instructions", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            "id", "quiz", "quiz_title", "quiz_course",
            "user_id", "status", "started_at", "submitted_at",
            "attempt_number", "score", "percentage", "passed",
            "time_taken_seconds", "tab_violations",
            "time_remaining_seconds",
            "duration_minutes", "allow_back_navigation", "one_question_at_a_time",
            "randomize_questions", "allow_unanswered", "tab_block", "instructions",
            "questions", "responses",
        )
        read_only_fields = fields

    def get_time_remaining_seconds(self, obj: QuizAttempt) -> int | None:
        from django.utils import timezone
        if obj.status != "in_progress":
            return None
        elapsed = (timezone.now() - obj.started_at).total_seconds()
        remaining = obj.quiz.duration_minutes * 60 - elapsed
        return max(0, int(remaining))


class SaveResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    response = serializers.JSONField(allow_null=True)


class ResponseEvaluationSerializer(serializers.Serializer):
    response_id = serializers.IntegerField()
    marks_obtained = serializers.DecimalField(
        max_digits=6, decimal_places=2, allow_null=True
    )
    professor_feedback = serializers.CharField(required=False, allow_blank=True, default="")
    ai_suggested_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )


class EvaluateAttemptSerializer(serializers.Serializer):
    responses = ResponseEvaluationSerializer(many=True)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class QuizReportSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()
    quiz_title = serializers.CharField()
    total_submissions = serializers.IntegerField()
    average_score = serializers.DecimalField(
        max_digits=8, decimal_places=2, allow_null=True
    )
    highest_score = serializers.DecimalField(
        max_digits=8, decimal_places=2, allow_null=True
    )
    lowest_score = serializers.DecimalField(
        max_digits=8, decimal_places=2, allow_null=True
    )
    pass_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    submissions = QuizAttemptSerializer(many=True)


class SaveResponseResultSerializer(serializers.Serializer):
    saved = serializers.BooleanField()


class AddBankQuestionSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()


class ReleaseAllResultSerializer(serializers.Serializer):
    released = serializers.IntegerField()
