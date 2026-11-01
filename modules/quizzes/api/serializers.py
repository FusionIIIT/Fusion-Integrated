"""A student serializer never carries `is_correct` or `accepted_answers`."""
from __future__ import annotations

from rest_framework import serializers

from modules.quizzes.models import Attempt, Option, Question, Quiz


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ["question_type", "text", "marks", "negative_marks",
                  "accepted_answers", "options"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Quiz
        fields = ["id", "course_code", "title", "instructions", "status",
                  "opens_at", "closes_at", "duration_minutes", "max_attempts",
                  "shuffle_questions", "negative_marking", "questions"]
        read_only_fields = ["id", "status"]

    def validate(self, attrs):
        if attrs["closes_at"] <= attrs["opens_at"]:
            raise serializers.ValidationError({"closes_at": "Must be after opens_at."})
        return attrs


class AttemptSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = ["id", "quiz", "status", "deadline", "score", "questions"]

    def get_questions(self, attempt) -> list[dict]:
        """The paper, in this attempt's fixed order, without the answer key."""
        if attempt.status != "in_progress":
            return []
        by_id = {q.id: q for q in attempt.quiz.questions.prefetch_related("options")}
        return [{"id": q.id, "question_type": q.question_type, "text": q.text,
                 "marks": str(q.marks),
                 "options": [{"id": o.id, "text": o.text} for o in q.options.all()]}
                for q in (by_id[i] for i in attempt.question_order if i in by_id)]


class SaveResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_ids = serializers.ListField(child=serializers.IntegerField(),
                                                required=False, default=list)
    text = serializers.CharField(required=False, allow_blank=True, default="")
