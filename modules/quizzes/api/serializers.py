"""Two views of a question: the professor's, with the key, and the student's,
without it. A student serializer never carries `is_correct`."""
from __future__ import annotations

from rest_framework import serializers

from modules.quizzes.domain import scoring
from modules.quizzes.models import Attempt, Option, Question, Quiz, Response

_QUIZ_SETTINGS = [
    "shuffle_questions", "shuffle_options", "allow_back_navigation",
    "one_question_at_a_time", "negative_marking", "allow_unanswered",
    "tab_block", "show_answers_on_release",
]


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "is_correct", "position"]
        read_only_fields = ["id", "position"]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ["id", "question_type", "text", "image", "marks", "negative_marks",
                  "accepted_answers", "course_code", "topic", "difficulty",
                  "position", "options"]
        read_only_fields = ["id", "position"]


class StudentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text"]


class StudentQuestionSerializer(serializers.ModelSerializer):
    options = StudentOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "question_type", "text", "image", "marks", "options"]


class QuizSerializer(serializers.ModelSerializer):
    max_marks = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "course_code", "title", "description", "instructions",
                  "status", "opens_at", "closes_at", "duration_minutes",
                  "passing_marks", "max_attempts", *_QUIZ_SETTINGS,
                  "max_marks", "question_count", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_question_count(self, quiz) -> int:
        return len(quiz.questions.all())

    def validate(self, attrs):
        opens = attrs.get("opens_at", getattr(self.instance, "opens_at", None))
        closes = attrs.get("closes_at", getattr(self.instance, "closes_at", None))
        if opens and closes and closes <= opens:
            raise serializers.ValidationError({"closes_at": "Must be after opens_at."})
        return attrs


class QuizDetailSerializer(QuizSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(QuizSerializer.Meta):
        fields = [*QuizSerializer.Meta.fields, "questions"]


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ["question", "selected_option_ids", "text", "awarded_marks", "feedback"]


class AttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    score = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = ["id", "quiz", "quiz_title", "student_user_id", "number", "status",
                  "started_at", "deadline", "submitted_at", "score", "responses"]

    def _visible(self, attempt) -> bool:
        """Marks reach a student only after release (BR-QZ-021)."""
        return self.context.get("as_professor") or attempt.status == "released"

    def get_score(self, attempt) -> str | None:
        return str(attempt.score) if self._visible(attempt) and attempt.score is not None \
            else None

    def get_responses(self, attempt) -> list[dict]:
        rows = ResponseSerializer(attempt.responses.all(), many=True).data
        if not self._visible(attempt):
            for row in rows:
                row["awarded_marks"] = row["feedback"] = None
        return rows


class AttemptPaperSerializer(AttemptSerializer):
    """What the student answers from: questions in their fixed order."""
    questions = serializers.SerializerMethodField()

    class Meta(AttemptSerializer.Meta):
        fields = [*AttemptSerializer.Meta.fields, "questions"]

    def get_questions(self, attempt) -> list[dict]:
        by_id = {q.id: q for q in attempt.quiz.questions.prefetch_related("options")}
        ordered = [by_id[i] for i in attempt.question_order if i in by_id]
        return StudentQuestionSerializer(ordered, many=True).data


class SaveResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_ids = serializers.ListField(child=serializers.IntegerField(),
                                                required=False, default=list)
    text = serializers.CharField(required=False, allow_blank=True, default="")


class GradeSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class CopyFromBankSerializer(serializers.Serializer):
    question_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)


class BankFilterSerializer(serializers.Serializer):
    course_code = serializers.CharField(required=False, default="")
    topic = serializers.CharField(required=False, default="")
    difficulty = serializers.CharField(required=False, default="")
    question_type = serializers.ChoiceField(choices=scoring.QUESTION_TYPES,
                                            required=False, default="")
    search = serializers.CharField(required=False, default="")
